"""Network-free CPU checks for Safe Start evaluation overlap screening."""
import contextlib
import gzip
import hashlib
from io import BytesIO, StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from diagnostics import safe_start_overlap as a


def candidates():
    return [dict(question_id=f"gsm8k-train-{i:05d}",
                 question=(f"At the {hashlib.sha256(str(i).encode()).hexdigest()[:18]} observatory "
                           f"researcher {hashlib.sha256(str(i).encode()).hexdigest()[18:36]} "
                           f"gathered {i+21} apricots. How many would remain after giving {i+1} away?"),
                 gold_answer=str(20), source="gsm8k", source_revision=a.DATASET_REVISION,
                 split="train", task="math") for i in range(12)]


def fixture(source, matching=None):
    name, typ = source["name"], source["format"]
    text = matching or f"Find the function value for a completely unrelated evaluation scenario {name}."
    if typ == "svamp":
        return json.dumps([{"Body": text, "Question": "How many total?", "Answer": 42}]).encode()
    if typ == "mbpp":
        return (json.dumps({"prompt": text, "task_id": 1,
                            "reference_solution": "SECRET SHOULD NOT LEAK"}) + "\n").encode()
    if typ == "ifeval":
        return (json.dumps({"prompt": text, "key": 1, "instruction_id_list": []}) + "\n").encode()
    return (json.dumps({"question": [[{"role": "user", "content": text}]],
                        "id": name, "ground_truth": "SECRET"}) + "\n").encode()


def setup_files(root):
    questions = root / 'questions.jsonl'
    report = root / 'selection-report.json'
    original = candidates()
    questions.write_text(''.join(json.dumps(x) + '\n' for x in original), encoding='utf-8')
    hashes = [hashlib.sha256(r['question'].encode()).hexdigest() for r in original]
    report.write_text(json.dumps({"status": "review_only", "training_approved": False,
                                  "dataset_revision": a.DATASET_REVISION,
                                  "train_parquet_sha256": "ea82612ea9582142387730c793eb67d3b12849002bc0b7fa6f8efafa7351419d",
                                  "selected_question_ids": [r['question_id'] for r in original],
                                  "selected_question_sha256": hashes}), encoding='utf-8')
    return questions, report


class TestSafeStartOverlap(unittest.TestCase):
    def test_six_pinned_sources_four_families(self):
        self.assertEqual(len(a.SOURCES), 6)
        self.assertEqual({s['family'] for s in a.SOURCES}, {'SVAMP', 'MBPP+', 'BFCL', 'IFEval'})
        self.assertTrue(all(s['url'].startswith('https://') for s in a.SOURCES))
        self.assertTrue(all('main/' not in s['url'] for s in a.SOURCES))

    def test_source_data_only_not_official_eval_runner(self):
        names = [s['name'] for s in a.SOURCES]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all('bfcl_eval/data/' in s['url'] for s in a.SOURCES if s['family'] == 'BFCL'))

    def test_fetch_known_sha_and_failure_without_network(self):
        payload = b'expected source bytes'
        expected = hashlib.sha256(payload).hexdigest()
        def fake_open(_url, timeout):
            return BytesIO(payload)
        source = {'name': 'example', 'format': 'svamp', 'url': 'https://example.test/blob',
                  'expected_sha256': expected}
        self.assertEqual(a.fetch_source(source, fake_open), (payload, expected))
        source['expected_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            a.fetch_source(source, fake_open)

    def test_mbpp_gzip_checksum_is_of_decoded_content(self):
        payload = fixture(a.SOURCES[1])
        s = {**a.SOURCES[1], 'expected_sha256': hashlib.sha256(payload).hexdigest()}
        raw = gzip.compress(payload)
        actual, digest = a.fetch_source(s, lambda url, timeout: BytesIO(raw))
        self.assertEqual(actual, payload)
        self.assertEqual(digest, s['expected_sha256'])

    def test_download_empty_rejected(self):
        with self.assertRaisesRegex(ValueError, 'empty'):
            a.fetch_source(a.SOURCES[-1], lambda url, timeout: BytesIO(b''))

    def test_download_size_limit_rejected(self):
        with patch.object(a, 'MAX_DOWNLOAD_BYTES', 8):
            with self.assertRaisesRegex(ValueError, 'size limit'):
                a.fetch_source(a.SOURCES[-1], lambda url, timeout: BytesIO(b'X'*10))

    def test_invalid_source_schema_rejected(self):
        for s in a.SOURCES:
            bad = b'{}\n' if s['format'] != 'svamp' else b'[{"Body": "X"}]'
            with self.subTest(s=s['name']):
                with self.assertRaises(ValueError):
                    a.extract_prompts(s, bad)

    def test_extract_six_sources_and_ignore_answers(self):
        for s in a.SOURCES:
            prompts = a.extract_prompts(s, fixture(s))
            self.assertEqual(len(prompts), 1)
            self.assertNotIn('SECRET', repr(prompts))
            self.assertNotIn('42', ' '.join(prompts))

    def test_unsupported_bfcl_multiturn_rejected(self):
        data = json.dumps({'question': [[{'role':'user', 'content':'hey'}],
                                         [{'role':'user', 'content':'again'}]]}).encode()+b'\n'
        with self.assertRaisesRegex(ValueError, 'invalid prompt schema'):
            a.extract_prompts(a.SOURCES[2], data)

    def test_exact_and_near_matching(self):
        selected = candidates()
        texts = {s['name']: a.extract_prompts(s, fixture(s)) for s in a.SOURCES}
        norm = a.normalize_question(selected[0]['question'])
        texts['ifeval'] = [norm]
        texts['bfcl_simple_python'] = [a.normalize_question(selected[1]['question']+'!')]
        matches = a.screen_questions(selected, texts)
        self.assertEqual({m['question_id'] for m in matches},
                         {selected[0]['question_id'], selected[1]['question_id']})
        self.assertEqual({m['source'] for m in matches}, {'ifeval', 'bfcl_simple_python'})

    def test_partial_source_list_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing or unexpected'):
            a.screen_questions(candidates(), {'svamp': ['some text']})

    def test_empty_source_list_rejected(self):
        data = {s['name']: ['hello'] for s in a.SOURCES}
        data['svamp'] = []
        with self.assertRaisesRegex(ValueError, 'missing prompts'):
            a.screen_questions(candidates(), data)

    def test_question_hash_tampering_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            q,r = setup_files(Path(folder))
            self.assertEqual(len(a.verify_selection(q,r)[0]), 12)
            payload = json.loads(r.read_text())
            payload['selected_question_sha256'][0] = '0'*64
            r.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, 'do not match'):
                a.verify_selection(q,r)

    def test_missing_selection_file_fails_before_network(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(FileNotFoundError):
                a.audit(root/'missing.jsonl',root/'selection-report.json',root/'overlap-audit.json',
                        fetcher=lambda s: self.fail('must not fetch'))

    def test_clean_audit_does_not_claim_no_contamination(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            q,r=setup_files(root)
            before_q, before_r=q.read_bytes(),r.read_bytes()
            def fetch(s):
                body=fixture(s)
                return body,hashlib.sha256(body).hexdigest()
            out=root/'overlap-audit.json'
            report=a.audit(q,r,out,fetch)
            self.assertEqual(report['audit_result'],'no_matches_in_screened_sources')
            self.assertFalse(report['overlap_audit_exhaustive'])
            self.assertFalse(report['semantic_paraphrases_ruled_out'])
            self.assertFalse(report['training_approved'])
            self.assertFalse(report['gpu_used'])
            self.assertFalse(report['official_benchmark_run'])
            self.assertEqual(len(report['sources']),6)
            self.assertEqual(report['screened_families'],['BFCL','IFEval','MBPP+','SVAMP'])
            self.assertEqual(q.read_bytes(),before_q)
            self.assertEqual(r.read_bytes(),before_r)
            self.assertTrue(out.is_file())
            self.assertNotIn('SECRET', out.read_text())
            with self.assertRaises(FileExistsError):
                a.audit(q,r,out,lambda s: self.fail('must not fetch'))

    def test_partial_download_does_not_write_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            q,r=setup_files(root)
            calls=[]
            def fetch(s):
                calls.append(s['name'])
                if len(calls)==3:
                    raise ValueError('broken remote')
                body=fixture(s)
                return body,hashlib.sha256(body).hexdigest()
            with self.assertRaisesRegex(ValueError,'broken remote'):
                a.audit(q,r,root/'overlap-audit.json',fetch)
            self.assertFalse((root/'overlap-audit.json').exists())

    def test_cli_never_downloads_implicitly(self):
        with contextlib.redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as exc:
                a.main([])
        self.assertEqual(exc.exception.code,2)

    def test_cli_explicit_download_mocked(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            q,r=setup_files(root)
            def fetch(s):
                body=fixture(s)
                return body,hashlib.sha256(body).hexdigest()
            with patch.object(a,'fetch_source',side_effect=fetch):
                # main -> audit default uses bound fetch_source at definition time;
                # mock audit instead, while testing its main wiring separately.
                with patch.object(a,'audit',return_value={'status':'review_only'}) as fake:
                    with contextlib.redirect_stdout(StringIO()):
                        a.main(['--download','--questions',str(q),'--selection-report',str(r),
                                '--out',str(root/'overlap-audit.json')])
                    self.assertEqual(fake.call_count,1)


if __name__ == '__main__':
    unittest.main()
