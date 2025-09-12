class PersistentClient:
    def __init__(self, path: str | None = None):
        self._path = path

    class _Collection:
        def add(self, *args, **kwargs):
            pass

        def query(self, *args, **kwargs):
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

        def count(self):
            return 0

    def get_or_create_collection(self, name: str, metadata: dict | None = None):
        return self._Collection()
