
# Installation

You need to install Node.js first. For Mac, simply using Homebrew
```
brew install node
```
or using version control systems such as [nodebrew](https://github.com/hokaccha/nodebrew) or [n](https://github.com/tj/n).


First, you need install dependent packages.
Then, all of client JavaScript code will be compilied with [webpack](https://github.com/webpack/webpack) (something like Browserify).

```
$ cd static/react
$ npm install
$ webpack
Hash: 697320a8d972920674da
Version: webpack 1.13.2
Time: 6161ms
    Asset    Size  Chunks             Chunk Names
bundle.js  4.4 MB       0  [emitted]  main
   [0] multi main 40 bytes {0} [built]
    + 415 hidden modules
```

Since the client files are compiled to `bundle.js`, so simply include this in the bottom of the HTML file, then everything should be ok.
```
<script src="/static/react/bundle.js"></script>
```

Every time you edit the JavaScript files in `static/react`, then you need to run webpack to compile.
It's cumbersome, so I'll automate this (later when I have time).


