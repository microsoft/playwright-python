const fs = require('fs');

// Removes the sidebar on the landing page (/)
const indexPath = 'htmldocs/playwright/index.html';
let input = fs.readFileSync(indexPath).toString();
input = input.replace(/<nav id="sidebar">.*<\/nav>/s, '');
fs.writeFileSync(indexPath, input);
