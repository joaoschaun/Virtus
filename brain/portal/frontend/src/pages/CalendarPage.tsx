import { useState, useEffect } from 'react'
import { Calendar, AlertTriangle, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'

interface EconomicEvent {
  time: string
  time_brazil: string
  country: string
  event: string
  impact: string
  actual?: string
  forecast?: string
  previous?: string
}

const CalendarPage = () => {
  const [events, setEvents] = useState<{
    all: EconomicEvent[]
    high: EconomicEvent[]
    medium: EconomicEvent[]
    low: EconomicEvent[]
  }>({ all: [], high: [], medium: [], low: [] })
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(0)
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    fetchCalendar()
  }, [days])

  const fetchCalendar = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/portal/calendar?days=${days}`)
      const data = await response.json()
      if (data.success) {
        setEvents(data.events)
      }
    } catch (error) {
      console.error('Erro ao buscar calendário:', error)
    } finally {
      setLoading(false)
    }
  }

  const getCountryFlag = (country: string) => {
    const flags: Record<string, string> = {
      'US': '🇺🇸', 'BR': '🇧🇷', 'EU': '🇪🇺', 'GB': '🇬🇧', 'JP': '🇯🇵', 
      'CN': '🇨🇳', 'DE': '🇩🇪', 'FR': '🇫🇷', 'IT': '🇮🇹', 'ES': '🇪🇸',
      'AU': '🇦🇺', 'CA': '🇨🇦', 'CH': '🇨🇭', 'NZ': '🇳🇿', 'MX': '🇲🇽',
    }
    return flags[country] || '🌍'
  }

  const getImpactStyle = (impact: string) => {
    if (impact === 'high') return {
      bg: 'bg-virtus-accent-danger/10',
      border: 'border-virtus-accent-danger/30',
      badge: 'bg-virtus-accent-danger/20 text-virtus-accent-danger',
      label: 'Alto'
    }
    if (impact === 'medium') return {
      bg: 'bg-virtus-accent-warning/10',
      border: 'border-virtus-accent-warning/30',
      badge: 'bg-virtus-accent-warning/20 text-virtus-accent-warning',
      label: 'Médio'
    }
    return {
      bg: 'bg-virtus-bg-tertiary',
      border: 'border-virtus-border-primary',
      badge: 'bg-virtus-bg-hover text-virtus-text-muted',
      label: 'Baixo'
    }
  }

  const getDateLabel = () => {
    const date = new Date()
    date.setDate(date.getDate() + days)
    
    if (days === 0) return 'Hoje'
    if (days === 1) return 'Amanhã'
    
    return date.toLocaleDateString('pt-BR', { 
      weekday: 'long', 
      day: 'numeric', 
      month: 'long' 
    })
  }

  const filteredEvents = filter === 'all' ? events.all 
    : filter === 'high' ? events.high 
    : filter === 'medium' ? events.medium 
    : events.low

  const impactFilters = [
    { value: 'all', label: 'Todos', count: events.all.length },
    { value: 'high', label: 'Alto Impacto', count: events.high.length, color: 'text-virtus-accent-danger' },
    { value: 'medium', label: 'Médio', count: events.medium.length, color: 'text-virtus-accent-warning' },
    { value: 'low', label: 'Baixo', count: events.low.length, color: 'text-virtus-text-muted' },
  ]

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-virtus-text-primary flex items-center gap-3">
            <Calendar className="w-8 h-8 text-virtus-accent-primary" />
            Calendário Econômico
          </h1>
          <p className="text-virtus-text-secondary mt-2">
            Eventos que movimentam o mercado (horário de Brasília)
          </p>
        </div>

        {/* Day Selector */}
        <div className="flex items-center gap-2 bg-virtus-bg-card rounded-lg p-1">
          <button
            onClick={() => setDays(Math.max(0, days - 1))}
            disabled={days === 0}
            className="p-2 rounded-lg hover:bg-virtus-bg-hover disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-5 h-5 text-virtus-text-muted" />
          </button>
          <span className="px-4 py-2 text-virtus-text-primary font-medium min-w-[150px] text-center">
            {getDateLabel()}
          </span>
          <button
            onClick={() => setDays(Math.min(7, days + 1))}
            disabled={days === 7}
            className="p-2 rounded-lg hover:bg-virtus-bg-hover disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-5 h-5 text-virtus-text-muted" />
          </button>
        </div>
      </div>

      {/* Impact Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        {impactFilters.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
              filter === f.value
                ? 'bg-virtus-accent-primary text-white'
                : 'bg-virtus-bg-card text-virtus-text-secondary hover:bg-virtus-bg-hover'
            }`}
          >
            <span className={filter !== f.value ? f.color : ''}>{f.label}</span>
            <span className={`px-1.5 py-0.5 rounded text-xs ${
              filter === f.value ? 'bg-white/20' : 'bg-virtus-bg-hover'
            }`}>
              {f.count}
            </span>
          </button>
        ))}
      </div>

      {/* High Impact Alert */}
      {events.high.length > 0 && filter === 'all' && (
        <div className="bg-virtus-accent-danger/10 border border-virtus-accent-danger/30 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-virtus-accent-danger" />
            <span className="text-virtus-accent-danger font-medium">
              {events.high.length} evento(s) de alto impacto {days === 0 ? 'hoje' : 'neste dia'}
            </span>
          </div>
        </div>
      )}

      {/* Events List */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <RefreshCw className="w-8 h-8 text-virtus-accent-primary animate-spin" />
        </div>
      ) : (
        <div className="space-y-3">
          {filteredEvents.map((event, index) => {
            const style = getImpactStyle(event.impact)
            return (
              <div
                key={index}
                className={`${style.bg} border ${style.border} rounded-xl p-4 card-hover`}
              >
                <div className="flex flex-col md:flex-row md:items-center gap-4">
                  {/* Time & Country */}
                  <div className="flex items-center gap-4 md:w-32 flex-shrink-0">
                    <span className="text-2xl">{getCountryFlag(event.country)}</span>
                    <div>
                      <p className="text-virtus-accent-primary font-mono font-bold">{event.time_brazil}</p>
                      <p className="text-virtus-text-muted text-xs">{event.country}</p>
                    </div>
                  </div>

                  {/* Event */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${style.badge}`}>
                        {style.label}
                      </span>
                    </div>
                    <p className="text-virtus-text-primary font-medium">{event.event}</p>
                  </div>

                  {/* Values */}
                  <div className="flex gap-6 md:gap-8 text-sm">
                    {event.previous && (
                      <div>
                        <p className="text-virtus-text-muted text-xs">Anterior</p>
                        <p className="text-virtus-text-secondary font-mono">{event.previous}</p>
                      </div>
                    )}
                    {event.forecast && (
                      <div>
                        <p className="text-virtus-text-muted text-xs">Previsão</p>
                        <p className="text-virtus-accent-warning font-mono">{event.forecast}</p>
                      </div>
                    )}
                    {event.actual && (
                      <div>
                        <p className="text-virtus-text-muted text-xs">Atual</p>
                        <p className="text-virtus-accent-success font-mono font-bold">{event.actual}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {!loading && filteredEvents.length === 0 && (
        <div className="text-center py-20">
          <Calendar className="w-12 h-12 text-virtus-text-muted mx-auto mb-4" />
          <p className="text-virtus-text-secondary">Nenhum evento encontrado para este dia</p>
        </div>
      )}
    </div>
  )
}

export default CalendarPage
