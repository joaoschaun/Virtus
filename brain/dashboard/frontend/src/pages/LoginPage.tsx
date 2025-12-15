import { useState, FormEvent } from 'react'
import { useAuthStore } from '../stores/authStore'
import { Eye, EyeOff, Loader2 } from 'lucide-react'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  
  const { login, isLoading, error, clearError } = useAuthStore()
  
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    clearError()
    
    if (!username || !password) return
    
    await login(username, password)
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Video Background */}
      <video
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 w-full h-full object-cover"
      >
        <source src="/virtus-brain.mp4" type="video/mp4" />
      </video>
      
      {/* Dark Overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-black/80 via-black/70 to-black/80" />
      
      {/* Subtle animated accents */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-virtus-accent-primary/10 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-red-500/10 rounded-full blur-[100px] animate-pulse" style={{ animationDelay: '1s' }} />
      </div>
      
      {/* Login Card */}
      <div className="relative z-10 w-full max-w-md px-4">
        {/* Logo Section */}
        <div className="text-center mb-8">
          {/* Logo */}
          <div className="flex justify-center mb-6">
            <img 
              src="/virtus-assinatura.png" 
              alt="Virtus Investimentos" 
              className="h-20 md:h-24 w-auto"
            />
          </div>
          
          {/* Tagline */}
          <p className="text-white/50 text-sm tracking-wide">
            Trading Dashboard
          </p>
        </div>
        
        {/* Form Card */}
        <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl">
          <h2 className="text-xl font-semibold text-center mb-6 text-white">
            Bem-vindo de volta
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">Usuário</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className={`w-full px-4 py-3 bg-white/5 border ${error ? 'border-red-500/50' : 'border-white/10'} rounded-xl text-white placeholder-white/30 focus:outline-none focus:border-red-500/50 focus:ring-2 focus:ring-red-500/20 transition-all`}
                placeholder="Digite seu usuário"
                autoComplete="username"
                autoFocus
              />
            </div>
            
            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-white/70 mb-2">Senha</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={`w-full px-4 py-3 pr-12 bg-white/5 border ${error ? 'border-red-500/50' : 'border-white/10'} rounded-xl text-white placeholder-white/30 focus:outline-none focus:border-red-500/50 focus:ring-2 focus:ring-red-500/20 transition-all`}
                  placeholder="Digite sua senha"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/70 transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>
            
            {/* Error Message */}
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}
            
            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || !username || !password}
              className="w-full py-3.5 bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 disabled:from-gray-600 disabled:to-gray-500 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all duration-300 flex items-center justify-center gap-2 shadow-lg shadow-red-500/20 hover:shadow-red-500/40"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Entrando...</span>
                </>
              ) : (
                <span>Entrar</span>
              )}
            </button>
          </form>
          
          {/* Demo Credentials */}
          <div className="mt-6 pt-6 border-t border-white/10">
            <p className="text-xs text-white/40 text-center mb-3">
              Credenciais de demonstração:
            </p>
            <div className="flex gap-3 text-xs">
              <button
                type="button"
                onClick={() => {
                  setUsername('admin')
                  setPassword('virtus2024!')
                }}
                className="flex-1 p-3 bg-white/5 rounded-xl hover:bg-white/10 transition-colors text-center border border-white/5 hover:border-white/10"
              >
                <p className="font-medium text-white/90">Admin</p>
                <p className="text-white/40 mt-1">virtus2024!</p>
              </button>
              <button
                type="button"
                onClick={() => {
                  setUsername('trader')
                  setPassword('trader123')
                }}
                className="flex-1 p-3 bg-white/5 rounded-xl hover:bg-white/10 transition-colors text-center border border-white/5 hover:border-white/10"
              >
                <p className="font-medium text-white/90">Trader</p>
                <p className="text-white/40 mt-1">trader123</p>
              </button>
            </div>
          </div>
        </div>
        
        {/* Footer */}
        <p className="text-center text-xs text-white/30 mt-6">
          © 2024 VIRTUS Investimentos. Todos os direitos reservados.
        </p>
      </div>
    </div>
  )
}
