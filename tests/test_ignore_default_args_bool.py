def test_ignore_default_args_false_is_removed():
    # Unit test: no driver/browser needed.
    from playwright._impl._browser_type import normalize_launch_params

    params = {"ignoreDefaultArgs": False}
    normalize_launch_params(params)

    assert "ignoreDefaultArgs" not in params
    assert "ignoreAllDefaultArgs" not in params


def test_ignore_default_args_true_sets_ignore_all_default_args():
    from playwright._impl._browser_type import normalize_launch_params

    params = {"ignoreDefaultArgs": True}
    normalize_launch_params(params)

    assert "ignoreDefaultArgs" not in params
    assert params["ignoreAllDefaultArgs"] is True


def test_ignore_default_args_list_is_preserved():
    from playwright._impl._browser_type import normalize_launch_params

    params = {"ignoreDefaultArgs": ["--mute-audio"]}
    normalize_launch_params(params)

    assert params["ignoreDefaultArgs"] == ["--mute-audio"]
    assert "ignoreAllDefaultArgs" not in params
