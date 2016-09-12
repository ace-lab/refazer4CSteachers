let reducer = function (state, action) {
  switch (action.type) {
    case 'INIT_CODE':
      return Object.assign({}, state, {
        code: action.code
      })
    case 'INIT_STATE':
      return Object.assign({}, state,
        action.state
      )
    case 'UPDATE_STEP':
      let step = action.step
      if (state.stream.length <= step) return state
      let line = state.stream[step].line
      let height = 35 + 21 * (line - 1)
      return Object.assign({}, state, {
        step: step,
        height: height,
        error: false
      })
    case 'STOP_PLAY':
      return Object.assign({}, state, {
        error: false
      })
    default:
      return state
  }
}

export default reducer