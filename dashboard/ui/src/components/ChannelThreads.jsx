import React, { useState, useEffect } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import Stakeholders from './Stakeholders'


const ChannelThreads = () => {
  const navigate = useNavigate()
  const { channelId } = useParams()
  const location = useLocation()
  const [channel, setChannel] = useState(location.state?.channel || null)
  const [threads, setThreads] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all') // all, active, high, medium, low

  useEffect(() => {
    fetchThreads()
  }, [channel, filter])

  const fetchThreads = async () => {
    try {
      setLoading(true)
      setError(null)
      
      let url = `/api/threads?channel=${encodeURIComponent(channel.channel_name)}&limit=50`
      
      // Add priority filter if not 'all'
      if (filter !== 'all' && filter !== 'active') {
        url += `&priority=${filter}`
      }
      
      const response = await fetch(url)
      if (!response.ok) {
        throw new Error('Failed to fetch threads')
      }
      const threadsData = await response.json()
      
      // Filter active threads if needed
      let filteredThreads = threadsData || []
      if (filter === 'active') {
        filteredThreads = filteredThreads.filter(thread => thread.status === 'open')
      }
      
      setThreads(filteredThreads)
    } catch (error) {
      console.error('Error fetching threads:', error)
      setError(error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleBackToChannels = () => {
    navigate('/')
  }

  // If no channel data from navigation state, fetch it using channelId
  useEffect(() => {
    if (!channel && channelId) {
      fetchChannelData()
    }
  }, [channelId, channel])

  const fetchChannelData = async () => {
    try {
      const response = await fetch('/api/channels')
      if (response.ok) {
        const channels = await response.json()
        const foundChannel = channels.find(c => c.channel_id === channelId)
        if (foundChannel) {
          setChannel(foundChannel)
        }
      }
    } catch (error) {
      console.error('Error fetching channel data:', error)
    }
  }

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'high':
        return <Badge variant="destructive">🔴 HIGH</Badge>
      case 'medium':
        return <Badge variant="warning">🟡 MEDIUM</Badge>
      case 'low':
        return <Badge variant="success">🟢 LOW</Badge>
      default:
        return <Badge variant="secondary">⚪ NONE</Badge>
    }
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'open':
        return <Badge variant="warning">OPEN</Badge>
      case 'closed':
        return <Badge variant="success">CLOSED</Badge>
      case 'resolved':
        return <Badge variant="info">RESOLVED</Badge>
      default:
        return <Badge variant="secondary">{status.toUpperCase()}</Badge>
    }
  }

  const formatTimeAgo = (timestamp) => {
    const now = new Date()
    const time = new Date(timestamp)
    const diffMs = now - time
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return `${diffDays}d ago`
  }

  const generateSlackThreadLink = (channelId, threadTs) => {
    // Convert thread timestamp to Slack link format
    const ts = threadTs.replace('.', '')
    return `slack://channel?team=T05H8RRPK0N&id=${channelId}&message=${ts}`
  }

  const parseStakeholders = (stakeholdersString) => {
    if (!stakeholdersString) return []
    
    // If it's already an array, return it
    if (Array.isArray(stakeholdersString)) return stakeholdersString
    
    if (typeof stakeholdersString === 'string') {
      // Try to parse as JSON first (handles "[\"U123\", \"U456\"]" format)
      try {
        const parsed = JSON.parse(stakeholdersString)
        if (Array.isArray(parsed)) {
          return parsed.filter(id => id && id.startsWith('U'))
        }
      } catch (e) {
        // If JSON parsing fails, fall back to comma/space splitting
        console.log('Fallback parsing for stakeholders:', stakeholdersString)
      }
      
      // Fallback: split by comma and space (handles "U123, U456" format)
      return stakeholdersString
        .split(/[,\s]+/)
        .map(id => id.trim())
        .filter(id => id.length > 0 && id.startsWith('U'))
    }
    
    return []
  }

  const filteredCount = threads.length
  const activeCount = threads.filter(t => t.status === 'open').length
  const highPriorityCount = threads.filter(t => t.priority === 'high').length

  if (loading) {
    return (
      <div className="min-h-screen p-6">
        <div className="max-w-6xl mx-auto">
          {/* Navigation Header */}
          <div className="mb-6">
            <nav className="flex items-center space-x-2 text-sm text-slate-600">
              <button 
                onClick={handleBackToChannels}
                className="font-semibold text-orange-600 hover:text-orange-700 transition-colors"
              >
                🏠 Dashboard
              </button>
              <span>/</span>
              <span>Channels</span>
              <span>/</span>
              <span className="font-semibold">#{channel?.channel_name || 'Loading...'}</span>
            </nav>
          </div>
          <div className="flex items-center justify-center h-96">
            <div className="text-center space-y-4">
              <div className="animate-spin rounded-full h-16 w-16 border-4 border-orange-200 border-t-orange-500 mx-auto"></div>
              <div className="space-y-2">
                <p className="text-xl font-semibold text-slate-700">Loading threads...</p>
                <p className="text-slate-500">Fetching discussions for this channel</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen p-6">
        <div className="max-w-6xl mx-auto">
          {/* Navigation Header */}
          <div className="mb-6">
            <nav className="flex items-center space-x-2 text-sm text-slate-600">
              <button 
                onClick={handleBackToChannels}
                className="font-semibold text-blue-600"
              >
                🏠 Dashboard
              </button>
              <span>/</span>
              <span>Channels</span>
              <span>/</span>
              <span className="font-semibold">#{channel?.channel_name || 'Error'}</span>
            </nav>
          </div>
          <Card className="border-red-300 bg-red-50/50 shadow-xl">
            <CardHeader className="bg-red-50 border-b border-red-200">
              <CardTitle className="text-red-700 text-xl font-bold">⚠️ Error Loading Threads</CardTitle>
              <CardDescription className="text-red-600">{error}</CardDescription>
            </CardHeader>
            <CardContent className="p-6 space-x-4">
              <Button 
                onClick={fetchThreads}
                className="bg-red-600 text-white"
              >
                🔄 Try Again
              </Button>
              <Button 
                onClick={handleBackToChannels} 
                className="bg-slate-100 text-slate-700 border border-slate-300 hover:bg-slate-200"
              >
                ← Back to Channels
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-6 bg-slate-50">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Navigation Header */}
        <div className="mb-6">
          <nav className="flex items-center space-x-2 text-sm text-slate-600">
            <button 
              onClick={handleBackToChannels}
              className="font-semibold text-blue-600"
            >
              🏠 Dashboard
            </button>
            <span>/</span>
            <span>Channels</span>
            <span>/</span>
            <span className="font-semibold">#{channel?.channel_name}</span>
          </nav>
        </div>

        {/* Header */}
        <div className="bg-white rounded-lg p-6 border border-slate-200 shadow-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button 
                onClick={handleBackToChannels}
                className="bg-slate-100 text-slate-700 border border-slate-300"
                size="sm"
              >
                ← Back to Channels
              </Button>
              <div className="w-12 h-12 bg-blue-500 rounded-lg flex items-center justify-center shadow-lg">
                <span className="text-white font-bold text-xl">#</span>
              </div>
              <div>
                <h1 className="text-3xl font-bold text-slate-800">#{channel?.channel_name}</h1>
                <p className="text-slate-600">{channel?.purpose?.value || 'Channel threads and discussions'}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Stats Overview */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <Card className="yb-stats-card border-l-4 border-l-blue-500">
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-blue-600 font-bold text-sm">{filteredCount}</span>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-600">{filteredCount}</div>
                  <p className="text-sm text-slate-500">Total Threads</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="yb-stats-card border-l-4 border-l-orange-500">
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                  <span className="text-orange-600 font-bold text-sm">{activeCount}</span>
                </div>
                <div>
                  <div className="text-2xl font-bold text-orange-600">{activeCount}</div>
                  <p className="text-sm text-slate-500">Active Threads</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="yb-stats-card border-l-4 border-l-red-500">
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                  <span className="text-red-600 font-bold text-sm">{highPriorityCount}</span>
                </div>
                <div>
                  <div className="text-2xl font-bold text-red-600">{highPriorityCount}</div>
                  <p className="text-sm text-slate-500">High Priority</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="yb-stats-card border-l-4 border-l-purple-500">
            <CardContent className="p-6">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                  <span className="text-purple-600 font-bold text-sm">{threads.filter(t => t.ai_thread_name).length}</span>
                </div>
                <div>
                  <div className="text-2xl font-bold text-purple-600">
                    {threads.filter(t => t.ai_thread_name).length}
                  </div>
                  <p className="text-sm text-slate-500">AI Analyzed</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="bg-white/70 backdrop-blur-sm border border-slate-200 shadow-lg">
          <CardHeader className="bg-slate-50">
            <CardTitle className="text-xl font-bold text-slate-800">Filter Threads</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="flex flex-wrap gap-3">
              <Button 
                className={filter === 'all' ? 'yb-button-primary' : 'bg-white text-slate-700 border border-slate-300'}
                size="sm"
                onClick={() => setFilter('all')}
              >
                📊 All ({filteredCount})
              </Button>
              <Button 
                className={filter === 'active' ? 'yb-button-primary' : 'bg-white text-slate-700 border border-slate-300'}
                size="sm"
                onClick={() => setFilter('active')}
              >
                🔥 Active ({activeCount})
              </Button>
              <Button 
                className={filter === 'high' ? 'yb-button-primary' : 'bg-white text-slate-700 border border-slate-300'}
                size="sm"
                onClick={() => setFilter('high')}
              >
                🔴 High Priority ({highPriorityCount})
              </Button>
              <Button 
                className={filter === 'medium' ? 'yb-button-primary' : 'bg-white text-slate-700 border border-slate-300'}
                size="sm"
                onClick={() => setFilter('medium')}
              >
                🟡 Medium ({threads.filter(t => t.priority === 'medium').length})
              </Button>
              <Button 
                className={filter === 'low' ? 'yb-button-primary' : 'bg-white text-slate-700 border border-slate-300'}
                size="sm"
                onClick={() => setFilter('low')}
              >
                🟢 Low ({threads.filter(t => t.priority === 'low').length})
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Threads List */}
        <Card className="bg-white border border-slate-200 shadow-xl">
          <CardHeader className="bg-slate-50">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-2xl font-bold text-slate-800">Thread Activity</CardTitle>
                <CardDescription className="text-slate-600 mt-1">
                  Open discussions requiring attention in #{channel?.channel_name}
                </CardDescription>
              </div>
              <div className="flex space-x-2">
                <Button 
                  onClick={fetchThreads}
                  className="yb-button-primary"
                  size="sm"
                  disabled={loading}
                >
                  {loading ? '🔄' : '↻'} {loading ? 'Loading...' : 'Refresh'}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6">
            <div className="space-y-6">
              {threads.length === 0 ? (
                <div className="text-center py-16">
                  <div className="w-20 h-20 bg-slate-100 rounded-full mx-auto mb-6 flex items-center justify-center">
                    <svg
                      className="h-10 w-10 text-slate-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2 2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
                      />
                    </svg>
                  </div>
                  <p className="font-semibold text-slate-700 text-lg mb-2">No threads found</p>
                  <p className="text-slate-500">
                    {filter === 'all' 
                      ? 'This channel has no tracked threads yet.'
                      : `No threads match the "${filter}" filter.`
                    }
                  </p>
                </div>
              ) : (
                threads.map((thread, index) => (
                  <div key={index} className="bg-white border border-slate-200 rounded-xl p-6">
                    <div className="flex items-start justify-between space-x-6">
                      <div className="flex-1 space-y-4">
                        <div className="flex items-center space-x-3 flex-wrap">
                          <h3 className="font-bold text-lg text-slate-800">
                            {thread.ai_thread_name || 'Thread Discussion'}
                          </h3>
                          {getPriorityBadge(thread.priority)}
                          {getStatusBadge(thread.status)}
                        </div>
                        
                        <p className="text-slate-600 leading-relaxed">
                          {thread.ai_description || 'No description available'}
                        </p>
                        
                        <div className="flex items-center space-x-6 text-sm text-slate-500 flex-wrap bg-slate-50 rounded-lg p-3">
                          <span className="flex items-center space-x-1">
                            <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
                            <span>{thread.reply_count} replies</span>
                          </span>
                          <span className="flex items-center space-x-1">
                            <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                            <span>Last: {formatTimeAgo(thread.latest_reply)}</span>
                          </span>
                          <span className="flex items-center space-x-1">
                            <span className="w-2 h-2 bg-purple-400 rounded-full"></span>
                            <span>Created: {formatTimeAgo(thread.created_at)}</span>
                          </span>
                        </div>
                        
                        {/* Stakeholders Section */}
                        {thread.ai_stakeholders && parseStakeholders(thread.ai_stakeholders).length > 0 && (
                                                      <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                            <div className="flex items-center space-x-2">
                              <span className="text-sm font-medium text-slate-700">👥 Stakeholders:</span>
                              <Stakeholders 
                                stakeholderIds={parseStakeholders(thread.ai_stakeholders)}
                                maxVisible={3}
                              />
                            </div>
                          </div>
                        )}
                        
                        {(thread.github_issue || thread.jira_ticket || thread.thread_issue) && (
                          <div className="flex items-center space-x-3 flex-wrap">
                            {thread.github_issue && (
                              <Badge className="bg-gray-100 text-gray-800 border border-gray-300">
                                🐙 GitHub: {thread.github_issue}
                              </Badge>
                            )}
                            {thread.jira_ticket && (
                              <Badge className="bg-blue-100 text-blue-800 border border-blue-300">
                                🎫 JIRA: {thread.jira_ticket}
                              </Badge>
                            )}
                            {thread.thread_issue && (
                              <Badge className="bg-red-100 text-red-800 border border-red-300">
                                ⚠️ Issue: {thread.thread_issue}
                              </Badge>
                            )}
                          </div>
                        )}
                      </div>
                      
                      <div className="flex flex-col space-y-3 items-center">
                        <Button 
                          className="bg-blue-500 text-white shadow-lg"
                          size="sm"
                          onClick={() => {
                            const slackLink = generateSlackThreadLink(thread.channel_id, thread.thread_ts)
                            window.open(slackLink, '_blank')
                          }}
                          title="Open thread in Slack"
                        >
                          💬 View in Slack
                        </Button>
                        <a 
                          href={`https://app.slack.com/client/T05H8RRPK0N/${thread.channel_id}/thread/${thread.channel_id}-${thread.thread_ts}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 underline"
                        >
                          Open in browser
                        </a>
                        {thread.ai_confidence && (
                          <div className="text-center bg-purple-50 rounded-lg p-2 border border-purple-200">
                            <div className="text-xs text-purple-600 font-medium">AI Confidence</div>
                            <div className="text-sm font-bold text-purple-700">
                              {Math.round(thread.ai_confidence * 100)}%
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default ChannelThreads 