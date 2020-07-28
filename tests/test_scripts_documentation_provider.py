from scripts.documentation_provider import DocumentationProvider


def test_transform_documentation_entry() -> None:
    provider = DocumentationProvider()
    assert provider._transform_doc_entry(["<[Promise]<?[Error]>>"]) == [
        "<Optional[Error]>"
    ]
    assert provider._transform_doc_entry(["<[Frame]>"]) == ["<Frame>"]
    assert provider._transform_doc_entry(["<[function]|[string]|[Object]>"]) == [
        "<[function]|[str]|[Dict]>"
    ]
    assert provider._transform_doc_entry(["<?[Object]>"]) == ["<Optional[Dict]>"]
