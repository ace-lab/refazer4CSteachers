import React, { Component } from 'react'
import Slider from 'rc-slider'
import { PrismCode } from 'react-prism'
import Prism from 'prismjs'
import '../node_modules/prismjs/components/prism-python'
import '../node_modules/prismjs/plugins/line-numbers/prism-line-numbers'

import Output from './Output'


class Code extends Component {

  playStep() {
    let timer = setInterval(() => {
      if (this.props.data.error || this.props.data.max <= this.props.data.step) {
        clearInterval(timer)
        this.props.actions.stopPlay()
      } else {
        this.nextStep()
      }
    }, 100)
  }

  nextStep () {
    if (this.props.data.max <= this.props.data.step) return
    let step = this.props.data.step+1
    this.props.actions.updateStep(step)
  }

  updateStep(value) {
    let step = Math.floor(value)
    this.props.actions.updateStep(step)
  }

  render() {
    return (
      <div>
        <pre>
          <i id="tick" className="fa fa-arrow-right" style={{top: this.props.data.height}}></i>
          <PrismCode className="language-python line-numbers line-highlight" data-start="1" data-line="1">{this.props.data.code}</PrismCode>
          <Output
            store={this.props.store}
            code={this.props.data.code}
            step={this.props.data.step}
            traces={this.props.data.traces.slice(0, this.props.data.step)}
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
}

export default Code