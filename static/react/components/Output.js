import React, { Component } from 'react'
import watch from 'redux-watch'

class Output extends Component {

  render () {
    let outputs = {}
    this.props.stream.forEach( (data, i ) => {
      let line = data.line
      let output = data.output
      outputs[line] = output
    })

    let error
    try {
      let current = this.props.stream[this.props.step-1]
      error = {
        x: current.output.data,
        o: current.error.data
      }
    } catch (e) { }

    let errorStyle = {}
    if (error) {
      this.props.actions.stopPlay()
    }

    return (
      <div>
        <div id="output">
          {
            this.props.code.split('\n').map( (c, i) => {
              return (
                <div id={`line-${i+1}`}>
                  <If condition={outputs[i+1]}>
                    <span className='output-var'>{outputs[i+1].name}</span> = <span className='output-data'>{outputs[i+1].data}</span>
                  </If>
                </div>
              )
            })
          }
        </div>
        <div id="outer">
          <If condition={error}>
            <div id="error" className="ui left pointing red basic label">
              x: {error.x} o: {error.o}
            </div>
          </If>
        </div>
      </div>
    )
  }
}

export default Output