import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: ErrorInfo
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.setState({ errorInfo })
  }

  handleReload = () => {
    // Limpa localStorage e recarrega
    localStorage.removeItem('virtus-auth')
    window.location.href = '/login'
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen bg-[#0c0c10] flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-[#16161b] border border-[#2a2a32] rounded-xl p-8 text-center">
            <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertTriangle className="w-8 h-8 text-red-500" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Algo deu errado</h2>
            <p className="text-gray-400 mb-6">
              Ocorreu um erro ao carregar o dashboard. Por favor, tente novamente.
            </p>
            {this.state.error && (
              <p className="text-xs text-red-400 mb-4 font-mono bg-red-500/10 p-2 rounded">
                {this.state.error.message}
              </p>
            )}
            <button
              onClick={this.handleReload}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-red-600 to-red-500 text-white rounded-lg font-medium hover:opacity-90 transition-opacity"
            >
              <RefreshCw className="w-4 h-4" />
              Recarregar
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
