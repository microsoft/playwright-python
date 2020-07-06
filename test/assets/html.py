# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

button_html = """
<html>
  <head>
    <title>Button test</title>
  </head>
  <body>
    <script src="mouse-helper.js"></script>
    <button>Click target</button>
    <script>
      window.result = 'Was not clicked';
      window.offsetX = undefined;
      window.offsetY = undefined;
      window.pageX = undefined;
      window.pageY = undefined;
      window.shiftKey = undefined;
      window.pageX = undefined;
      window.pageY = undefined;
      window.bubbles = undefined;
      document.querySelector('button').addEventListener('click', e => {
        result = 'Clicked';
        offsetX = e.offsetX;
        offsetY = e.offsetY;
        pageX = e.pageX;
        pageY = e.pageY;
        shiftKey = e.shiftKey;
        bubbles = e.bubbles;
        cancelable = e.cancelable;
        composed = e.composed;
      }, false);
    </script>
  </body>
</html>
"""

textarea_html = """
<html>
  <head>
    <title>Textarea test</title>
  </head>
  <body>
    <textarea spellcheck="false"></textarea>
    <input></input>
    <div contenteditable="true"></div>
    <div class="plain">Plain div</div>
    <script src='mouse-helper.js'></script>
    <script>
      window.result = '';
      let textarea = document.querySelector('textarea');
      textarea.addEventListener('input', () => result = textarea.value, false);
      let input = document.querySelector('input');
      input.addEventListener('input', () => result = input.value, false);
    </script>
  </body>
</html>
"""
