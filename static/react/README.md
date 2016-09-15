
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
```html
<script src="/static/react/bundle.js"></script>
```

Every time you edit the JavaScript files in `static/react`, then you need to run webpack to compile.
It's cumbersome, so I'll automate this (later when I have time).

# Workflow

The core components are `components` directory: `App.js`, `Code.js`, and `Output.js`

## 1. Get the JSON data
First, the code is getting JSON data from `/static/react/sample/data-1.json`.
The data looks like this.
```json
{
  "stream" : [
    {
      "line": 1,
      "output": { "name": "n", "data": 3}
    },
    {
      "line": 2,
      "output": { "name": "i", "data": 3}
    },
    {
      "line": 3,
      "output": { "name": "product", "data": 3}
    },
    ...
  ]
}
```

When the HTML file is rendered, getting the data with the following code in `App.js`

```js
class App extends Component {
  componentDidMount() {
    $.get('/static/react/sample/data-1.json', function (res) {
      let state = {
        step: 0,
        stream: res.stream,
        max: res.stream.length-1,
        hints: res.hints
      }
      this.props.store.dispatch(actions.initState(state))
    }.bind(this))
  }
}
```

## 2. Show the data
React allows you to show the data with JSX. You can use the data anywhere from the React app. Just like this

![](http://reactfordesigners.com/labs/reactjs-introduction-for-people-who-know-just-enough-jquery-to-get-by/images/labs/jquery-style-vs-react-style.png)
From [React.js Introduction For People Who Know Just Enough jQuery To Get By](http://reactfordesigners.com/labs/reactjs-introduction-for-people-who-know-just-enough-jquery-to-get-by/)

This is main view in `App.js`

```jsx
render () {
  return (
    <div id="main" className="ui grid">
      <section id="container">
        <Code store={this.props.store} data={this.props} actions={this.props.actions}/>
      </section>
    </div>
  )
}
```

and `Code` will render with `Code.js`

```jsx
render() {
  return (
    <div>
      <pre>
        <i id="tick" className="fa fa-arrow-right" style={{top: this.props.data.height}}></i>
        <PrismCode className="language-python" data-line="1">{this.props.data.code}</PrismCode>
        <Output
          store={this.props.store}
          code={this.props.data.code}
          step={this.props.data.step}
          stream={this.props.data.stream.slice(0, this.props.data.step)}
          actions={this.props.actions}
        />
      </pre>
      <br />
      <Slider
        dots
        min={1}
        max={this.props.data.max}
        value={this.props.data.step}
        onChange={this.updateStep.bind(this)}
      />
      <br />
      <button className="ui button" onClick={this.playStep.bind(this)}><i className="fa fa-play"></i></button>
      <span>{this.props.data.step}</span>
    </div>
  )
}
```

## 3. Interacti with data

If you define the event handler, you can call function. For example, the following code callse `playStep` function when clicking the button

```html
<button className="ui button" onClick={this.nextStep.bind(this)}>Next</button>
```

You can access all of the data via `this.props` and update the data value.

```js
nextStep () {
  if (this.props.data.max <= this.props.data.step) return
  let step = this.props.data.step+1
  this.props.actions.updateStep(step)
}
```


