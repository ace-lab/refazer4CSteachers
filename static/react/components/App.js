import React, { Component } from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import actions from '../redux/actions'
import Code from './Code'
import _ from 'lodash'

class App extends Component {

  componentDidMount() {
    $.get('/static/react/sample/data-1.py', function (code) {
      console.log('app init code')
      this.props.store.dispatch(actions.initCode(code))
    }.bind(this))

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

  render () {
    return (
      <div id="main" className="ui grid">
        <section id="container" className="nine wide column">
          <Code store={this.props.store} data={this.props} actions={this.props.actions}/>
        </section>
      </div>
    )
  }
}

function mapStateToProps(state) {
  return state
}

function mapDispatchToProps(dispatch) {
  return {
    actions: bindActionCreators(actions, dispatch)
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(App)
