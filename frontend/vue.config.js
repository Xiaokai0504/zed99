const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  outputDir: 'dist',
  // 开发环境代理（本地运行时自动转发请求到后端）
  devServer: {
    proxy: {
      '/': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})