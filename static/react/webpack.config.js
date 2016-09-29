var webpack = require('webpack')
var path = require('path')

module.exports = {
  devtool: 'inline-source-map',
  entry: [
    'webpack-hot-middleware/client',
    './index.js'
  ],
  output: {
    path: './dist',
    filename: 'bundle.js',
    publicPath: '/'
  },
  plugins: [
    new webpack.optimize.OccurrenceOrderPlugin(),
    new webpack.HotModuleReplacementPlugin(),
    new webpack.NoErrorsPlugin()
  ],
  module: {
    loaders: [
      {
        test: /\.js$/,
        loader: 'babel-loader',
        exclude: /node_modules/,
        query: {
          presets: ['react', 'es2015', 'react-hmre']
        }
      }
    ]
  }
}