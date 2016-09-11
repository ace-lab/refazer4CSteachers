let actions = {
  initCode: function(code) {
    console.log('actions init code')
    return {
      type: 'INIT_CODE',
      code: code
    }
  },
  initState: function(state) {
    return {
      type: 'INIT_STATE',
      state: state
    }
  },
  updateStep: function(step) {
    return {
      type: 'UPDATE_STEP',
      step: step
    }
  },
  stopPlay: function() {
    return {
      type: 'STOP_PLAY',
    }
  }

}

export default actions