
def test_brand_guideline_tokens_and_honest_font_fallback():
    import tomllib
    from pathlib import Path
    path=Path('.streamlit/config.toml')
    assert path.exists(), 'Beacon theme must exist'
    theme=tomllib.loads(path.read_text())['theme']
    assert theme['primaryColor']=='#385981'
    css=Path('assets/beacon.css').read_text()
    for color in ['#1E343F','#385981','#F79122','#C44A4A','#388D58','#4A7CD0']:
        assert color in css
    assert 'sans-serif' in css and 'Menlo' in css
