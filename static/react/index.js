import React from 'react'
import { render } from 'react-dom'
import App from './components/App'
import configureStore from './redux/store'
import { Provider } from 'react-redux'

let initialStore = {
  code: '',
  step: 0,
  max: 0,
  error: '',
  hints: [],
  reveal: 0,
  traces: [{
    line: 0,
    output: []
  }],
  height: 35,
}

let store = configureStore(initialStore)

render(
  <Provider store={store}>
    <App store={store}/>
  </Provider>,
  document.getElementById('react-app')
)
