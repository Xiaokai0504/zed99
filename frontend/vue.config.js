// Vue CLI 4.x 最终兼容版（无任何语法错误）
module.exports = {
  // Vue CLI 4.x 必须是数组，空数组表示不转译任何第三方依赖
  transpileDependencies: [],
  // 构建输出目录
  outputDir: 'dist',
  // 静态资源目录（Vue CLI 4.x 默认即可）
  assetsDir: 'static',
  // 开发环境代理（本地运行时自动转发/api请求到后端）
  devServer: {
    port: 8080,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        pathRewrite: {
          '^/api': '/api'
        }
      }
    }
  }
}