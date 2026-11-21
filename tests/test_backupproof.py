import os, sys, tempfile, time, unittest, zipfile
sys.path.insert(0, ".")
from backupproof.core import prove

def make_tree(base, files):
    for rel, content in files.items():
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(content)

class FolderBackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = os.path.join(self.tmp.name, "src")
        self.bak = os.path.join(self.tmp.name, "bak")
        make_tree(self.src, {"a.txt": b"alpha", "sub/b.txt": b"beta"})
    def tearDown(self):
        self.tmp.cleanup()
    def test_identical_is_proven(self):
        make_tree(self.bak, {"a.txt": b"alpha", "sub/b.txt": b"beta"})
        result = prove(self.src, self.bak, use_hash=True)
        self.assertTrue(result["proven"])
    def test_missing_file(self):
        make_tree(self.bak, {"a.txt": b"alpha"})
        result = prove(self.src, self.bak)
        self.assertFalse(result["proven"])
        self.assertEqual(result["diff"]["missing"], ["sub/b.txt"])
    def test_same_size_different_content_needs_hash(self):
        make_tree(self.bak, {"a.txt": b"ALPHA", "sub/b.txt": b"beta"})
        self.assertTrue(prove(self.src, self.bak)["proven"])
        self.assertFalse(prove(self.src, self.bak, use_hash=True)["proven"])
    def test_stale_backup(self):
        make_tree(self.bak, {"a.txt": b"alpha", "sub/b.txt": b"beta"})
        old = time.time() - 100 * 3600
        for dirpath, _d, files in os.walk(self.bak):
            for name in files:
                os.utime(os.path.join(dirpath, name), (old, old))
        result = prove(self.src, self.bak, max_age_hours=48)
        self.assertFalse(result["proven"])

class ZipBackupTests(unittest.TestCase):
    def test_zip_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "src")
            make_tree(src, {"a.txt": b"alpha"})
            zpath = os.path.join(tmp, "backup.zip")
            with zipfile.ZipFile(zpath, "w") as archive:
                archive.writestr("a.txt", b"alpha")
            self.assertTrue(prove(src, zpath, use_hash=True)["proven"])
            with zipfile.ZipFile(zpath, "w") as archive:
                archive.writestr("a.txt", b"changed!")
            self.assertFalse(prove(src, zpath, use_hash=True)["proven"])

if __name__ == "__main__":
    unittest.main()
