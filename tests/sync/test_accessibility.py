# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest


def test_accessibility_should_work(page, is_firefox, is_chromium):
    page.set_content(
        """<head>
      <title>Accessibility Test</title>
    </head>
    <body>
      <h1>Inputs</h1>
      <input placeholder="Empty input" autofocus />
      <input placeholder="readonly input" readonly />
      <input placeholder="disabled input" disabled />
      <input aria-label="Input with whitespace" value="  " />
      <input value="value only" />
      <input aria-placeholder="placeholder" value="and a value" />
      <div aria-hidden="true" id="desc">This is a description!</div>
      <input aria-placeholder="placeholder" value="and a value" aria-describedby="desc" />
    </body>"""
    )
    # autofocus happens after a delay in chrome these days
    page.wait_for_function("document.activeElement.hasAttribute('autofocus')")

    if is_firefox:
        golden = {
            "role": "document",
            "name": "Accessibility Test",
            "children": [
                {"role": "heading", "name": "Inputs", "level": 1},
                {"role": "textbox", "name": "Empty input", "focused": True},
                {"role": "textbox", "name": "readonly input", "readonly": True},
                {"role": "textbox", "name": "disabled input", "disabled": True},
                {"role": "textbox", "name": "Input with whitespace", "value": "  "},
                {"role": "textbox", "name": "", "value": "value only"},
                {
                    "role": "textbox",
                    "name": "",
                    "value": "and a value",
                },  # firefox doesn't use aria-placeholder for the name
                {
                    "role": "textbox",
                    "name": "",
                    "value": "and a value",
                    "description": "This is a description!",
                },  # and here
            ],
        }
    elif is_chromium:
        golden = {
            "role": "WebArea",
            "name": "Accessibility Test",
            "children": [
                {"role": "heading", "name": "Inputs", "level": 1},
                {"role": "textbox", "name": "Empty input", "focused": True},
                {"role": "textbox", "name": "readonly input", "readonly": True},
                {"role": "textbox", "name": "disabled input", "disabled": True},
                {"role": "textbox", "name": "Input with whitespace", "value": "  "},
                {"role": "textbox", "name": "", "value": "value only"},
                {"role": "textbox", "name": "placeholder", "value": "and a value"},
                {
                    "role": "textbox",
                    "name": "placeholder",
                    "value": "and a value",
                    "description": "This is a description!",
                },
            ],
        }
    else:
        golden = {
            "role": "WebArea",
            "name": "Accessibility Test",
            "children": [
                {"role": "heading", "name": "Inputs", "level": 1},
                {"role": "textbox", "name": "Empty input", "focused": True},
                {"role": "textbox", "name": "readonly input", "readonly": True},
                {"role": "textbox", "name": "disabled input", "disabled": True},
                {"role": "textbox", "name": "Input with whitespace", "value": "  "},
                {"role": "textbox", "name": "", "value": "value only"},
                {"role": "textbox", "name": "placeholder", "value": "and a value"},
                {
                    "role": "textbox",
                    "name": "This is a description!",
                    "value": "and a value",
                },  # webkit uses the description over placeholder for the name
            ],
        }
    assert page.accessibility.snapshot() == golden


def test_accessibility_should_work_with_regular_text(page, is_firefox):
    page.set_content("<div>Hello World</div>")
    snapshot = page.accessibility.snapshot()
    assert snapshot["children"][0] == {
        "role": "text leaf" if is_firefox else "text",
        "name": "Hello World",
    }


def test_accessibility_roledescription(page):
    page.set_content('<div tabIndex=-1 aria-roledescription="foo">Hi</div>')
    snapshot = page.accessibility.snapshot()
    assert snapshot["children"][0]["roledescription"] == "foo"


def test_accessibility_orientation(page):
    page.set_content('<a href="" role="slider" aria-orientation="vertical">11</a>')
    snapshot = page.accessibility.snapshot()
    assert snapshot["children"][0]["orientation"] == "vertical"


def test_accessibility_autocomplete(page):
    page.set_content('<div role="textbox" aria-autocomplete="list">hi</div>')
    snapshot = page.accessibility.snapshot()
    assert snapshot["children"][0]["autocomplete"] == "list"


def test_accessibility_multiselectable(page):
    page.set_content('<div role="grid" tabIndex=-1 aria-multiselectable=true>hey</div>')
    snapshot = page.accessibility.snapshot()
    assert snapshot["children"][0]["multiselectable"]


def test_accessibility_keyshortcuts(page):
    page.set_content('<div role="grid" tabIndex=-1 aria-keyshortcuts="foo">hey</div>')
    snapshot = page.accessibility.snapshot()
    assert snapshot["children"][0]["keyshortcuts"] == "foo"


def test_accessibility_filtering_children_of_leaf_nodes_should_not_report_text_nodes_inside_controls(
    page, is_firefox
):
    page.set_content(
        """
    <div role="tablist">
    <div role="tab" aria-selected="true"><b>Tab1</b></div>
    <div role="tab">Tab2</div>
    </div>"""
    )
    golden = {
        "role": "document" if is_firefox else "WebArea",
        "name": "",
        "children": [
            {"role": "tab", "name": "Tab1", "selected": True},
            {"role": "tab", "name": "Tab2"},
        ],
    }
    assert page.accessibility.snapshot() == golden


# WebKit rich text accessibility is iffy
@pytest.mark.skip_browser("webkit")
def test_accessibility_filtering_children_of_leaf_nodes_rich_text_editable_fields_should_have_children(
    page, is_firefox
):
    page.set_content(
        """
    <div contenteditable="true">
    Edit this image: <img src="fakeimage.png" alt="my fake image">
    </div>"""
    )
    golden = (
        {
            "role": "section",
            "name": "",
            "children": [
                {"role": "text leaf", "name": "Edit this image: "},
                {"role": "text", "name": "my fake image"},
            ],
        }
        if is_firefox
        else {
            "role": "generic",
            "name": "",
            "value": "Edit this image: ",
            "children": [
                {"role": "text", "name": "Edit this image:"},
                {"role": "img", "name": "my fake image"},
            ],
        }
    )
    snapshot = page.accessibility.snapshot()
    assert snapshot["children"][0] == golden


# WebKit rich text accessibility is iffy
@pytest.mark.skip_browser("webkit")
def test_accessibility_filtering_children_of_leaf_nodes_rich_text_editable_fields_with_role_should_have_children(
    page, is_firefox, browser_channel
):
    page.set_content(
        """
    <div contenteditable="true" role='textbox'>
    Edit this image: <img src="fakeimage.png" alt="my fake image">
    </div>"""
    )
    if is_firefox:
        golden = {
            "role": "textbox",
            "name": "",
            "value": "Edit this image: my fake image",
            "children": [{"role": "text", "name": "my fake image"}],
        }
    else:
        if browser_channel:
            golden = {
                "role": "textbox",
                "name": "",
                "value": "Edit this image: ",
                "children": [
                    {"role": "text", "name": "Edit this image:"},
                    {"role": "img", "name": "my fake image"},
                ],
                "value": "Edit this image: ",
            }
        else:
            golden = {
                "role": "textbox",
                "name": "",
                "multiline": True,
                "value": "Edit this image: ",
                "children": [
                    {"role": "text", "name": "Edit this image:"},
                    {"role": "img", "name": "my fake image"},
                ],
                "value": "Edit this image: ",
            }
    snapshot = page.accessibility.snapshot()
    assert snapshot["children"][0] == golden


# Firefox does not support contenteditable="plaintext-only".
# WebKit rich text accessibility is iffy
@pytest.mark.only_browser("chromium")
def test_accessibility_plain_text_field_with_role_should_not_have_children(
    page, browser_channel
):
    page.set_content(
        """
    <div contenteditable="plaintext-only" role='textbox'>Edit this image:<img src="fakeimage.png" alt="my fake image"></div>"""
    )
    snapshot = page.accessibility.snapshot()
    if browser_channel:
        assert snapshot["children"][0] == {
            "name": "",
            "role": "textbox",
            "value": "Edit this image:",
        }
    else:
        assert snapshot["children"][0] == {
            "multiline": True,
            "name": "",
            "role": "textbox",
            "value": "Edit this image:",
        }


@pytest.mark.only_browser("chromium")
def test_accessibility_plain_text_field_without_role_should_not_have_content(
    page, browser_channel
):
    page.set_content(
        """
    <div contenteditable="plaintext-only">Edit this image:<img src="fakeimage.png" alt="my fake image"></div>"""
    )
    snapshot = page.accessibility.snapshot()
    if browser_channel:
        assert snapshot["children"][0] == {"name": "", "role": "generic"}
    else:
        assert snapshot["children"][0] == {
            "name": "",
            "role": "generic",
            "value": "Edit this image:",
        }


@pytest.mark.only_browser("chromium")
def test_accessibility_plain_text_field_with_tabindex_and_without_role_should_not_have_content(
    page, browser_channel
):
    page.set_content(
        """
    <div contenteditable="plaintext-only" tabIndex=0>Edit this image:<img src="fakeimage.png" alt="my fake image"></div>"""
    )
    snapshot = page.accessibility.snapshot()
    if browser_channel:
        assert snapshot["children"][0] == {"name": "", "role": "generic"}
    else:
        assert snapshot["children"][0] == {
            "name": "",
            "role": "generic",
            "value": "Edit this image:",
        }


def test_accessibility_non_editable_textbox_with_role_and_tabIndex_and_label_should_not_have_children(
    page, is_chromium, is_firefox
):
    page.set_content(
        """
      <div role="textbox" tabIndex=0 aria-checked="true" aria-label="my favorite textbox">
        this is the inner content
        <img alt="yo" src="fakeimg.png">
      </div>"""
    )
    if is_firefox:
        golden = {
            "role": "textbox",
            "name": "my favorite textbox",
            "value": "this is the inner content yo",
        }
    elif is_chromium:
        golden = {
            "role": "textbox",
            "name": "my favorite textbox",
            "value": "this is the inner content ",
        }
    else:
        golden = {
            "role": "textbox",
            "name": "my favorite textbox",
            "value": "this is the inner content  ",
        }
    snapshot = page.accessibility.snapshot()
    assert snapshot["children"][0] == golden


def test_accessibility_checkbox_with_and_tabIndex_and_label_should_not_have_children(
    page,
):
    page.set_content(
        """
    <div role="checkbox" tabIndex=0 aria-checked="true" aria-label="my favorite checkbox">
    this is the inner content
    <img alt="yo" src="fakeimg.png">
    </div>"""
    )
    golden = {"role": "checkbox", "name": "my favorite checkbox", "checked": True}
    snapshot = page.accessibility.snapshot()
    assert snapshot["children"][0] == golden


def test_accessibility_checkbox_without_label_should_not_have_children(
    page, is_firefox
):
    page.set_content(
        """
      <div role="checkbox" aria-checked="true">
        this is the inner content
        <img alt="yo" src="fakeimg.png">
    </div>"""
    )
    golden = {
        "role": "checkbox",
        "name": "this is the inner content yo",
        "checked": True,
    }
    snapshot = page.accessibility.snapshot()
    assert snapshot["children"][0] == golden


def test_accessibility_should_work_a_button(page):
    page.set_content("<button>My Button</button>")

    button = page.query_selector("button")
    assert page.accessibility.snapshot(root=button) == {
        "role": "button",
        "name": "My Button",
    }


def test_accessibility_should_work_an_input(page):
    page.set_content('<input title="My Input" value="My Value">')

    input = page.query_selector("input")
    assert page.accessibility.snapshot(root=input) == {
        "role": "textbox",
        "name": "My Input",
        "value": "My Value",
    }


def test_accessibility_should_work_on_a_menu(page, is_webkit):
    page.set_content(
        """
        <div role="menu" title="My Menu">
        <div role="menuitem">First Item</div>
        <div role="menuitem">Second Item</div>
        <div role="menuitem">Third Item</div>
        </div>
    """
    )

    menu = page.query_selector('div[role="menu"]')
    golden = {
        "role": "menu",
        "name": "My Menu",
        "children": [
            {"role": "menuitem", "name": "First Item"},
            {"role": "menuitem", "name": "Second Item"},
            {"role": "menuitem", "name": "Third Item"},
        ],
    }
    if is_webkit:
        golden["orientation"] = "vertical"
    assert page.accessibility.snapshot(root=menu) == golden


def test_accessibility_should_return_null_when_the_element_is_no_longer_in_DOM(
    page,
):
    page.set_content("<button>My Button</button>")
    button = page.query_selector("button")
    page.eval_on_selector("button", "button => button.remove()")
    assert page.accessibility.snapshot(root=button) is None


def test_accessibility_should_show_uninteresting_nodes(page):
    page.set_content(
        """
        <div id="root" role="textbox">
        <div>
            hello
            <div>
            world
            </div>
        </div>
        </div>
    """
    )

    root = page.query_selector("#root")
    snapshot = page.accessibility.snapshot(root=root, interesting_only=False)
    assert snapshot["role"] == "textbox"
    assert "hello" in snapshot["value"]
    assert "world" in snapshot["value"]
    assert snapshot["children"]
