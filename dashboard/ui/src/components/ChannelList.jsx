import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import Stakeholders from './Stakeholders'


const ChannelList = () => {
  const navigate = useNavigate()
  const [stats, setStats] = useState({
    totalThreads: 0,
    activeThreads: 0,
    channels: 0,
    aiAnalyzed: 0
  })
  const [channels, setChannels] = useState([])
  const [recentThreads, setRecentThreads] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchChannelData()
  }, [])

  const fetchChannelData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Fetch stats
      const statsResponse = await fetch('/api/stats')
      if (!statsResponse.ok) {
        throw new Error('Failed to fetch stats')
      }
      const statsData = await statsResponse.json()
      setStats(statsData)

      // Fetch channels
      const channelsResponse = await fetch('/api/channels')
      if (!channelsResponse.ok) {
        throw new Error('Failed to fetch channels')
      }
      const channelsData = await channelsResponse.json()
      setChannels(channelsData || [])

      // Fetch recent threads with stakeholders
      const threadsResponse = await fetch('/api/threads?limit=5')
      if (threadsResponse.ok) {
        const threadsData = await threadsResponse.json()
        setRecentThreads(threadsData || [])
      }
    } catch (error) {
      console.error('Error fetching channel data:', error)
      setError(error.message)
    } finally {
      setLoading(false)
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

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'high':
        return <Badge className="bg-red-100 text-red-800 border border-red-300">🔴 HIGH</Badge>
      case 'medium':
        return <Badge className="bg-yellow-100 text-yellow-800 border border-yellow-300">🟡 MEDIUM</Badge>
      case 'low':
        return <Badge className="bg-green-100 text-green-800 border border-green-300">🟢 LOW</Badge>
      default:
        return <Badge className="bg-gray-100 text-gray-800 border border-gray-300">⚪ NONE</Badge>
    }
  }

  const handleChannelSelect = (channel) => {
    navigate(`/channels/${channel.channel_id}/threads`, { 
      state: { channel } 
    })
  }

  if (loading) {
    return (
      <div className="min-h-screen p-6">
        <div className="max-w-6xl mx-auto">
          {/* Navigation Header */}
          <div className="mb-6">
            <nav className="flex items-center space-x-2 text-sm text-slate-600">
              <span className="font-semibold text-orange-600">🏠 Dashboard</span>
              <span>/</span>
              <span>Channels</span>
            </nav>
          </div>
          <div className="flex items-center justify-center h-96">
            <div className="text-center space-y-4">
              <div className="animate-spin rounded-full h-16 w-16 border-4 border-orange-200 border-t-orange-500 mx-auto"></div>
              <div className="space-y-2">
                <p className="text-xl font-semibold text-slate-700">Loading dashboard...</p>
                <p className="text-slate-500">Fetching channels and statistics</p>
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
              <span className="font-semibold text-orange-600">🏠 Dashboard</span>
              <span>/</span>
              <span>Channels</span>
            </nav>
          </div>
          <Card className="border-red-300 bg-red-50/50 shadow-xl">
            <CardHeader className="bg-red-50 border-b border-red-200">
              <CardTitle className="text-red-700 text-xl font-bold">⚠️ Error Loading Dashboard</CardTitle>
              <CardDescription className="text-red-600">{error}</CardDescription>
            </CardHeader>
            <CardContent className="p-6">
              <Button 
                onClick={fetchChannelData}
                className="bg-red-600 text-white"
              >
                🔄 Try Again
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
            <span className="font-semibold text-blue-600">🏠 Dashboard</span>
            <span>/</span>
            <span>Channels</span>
          </nav>
        </div>

        {/* Dashboard Header */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center space-x-2 bg-blue-50 px-6 py-3 rounded-full border border-blue-200">
            <span className="text-2xl">🧵</span>
            <h1 className="text-3xl font-bold text-blue-600">
              Open Threads Dashboard
            </h1>
          </div>
          <p className="text-slate-600 text-lg max-w-2xl mx-auto">
            Track and manage open discussions across your Slack channels with AI-powered insights
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <Card className="yb-stats-card border-l-4 border-l-orange-500">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-700">Total Threads</CardTitle>
              <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  className="h-5 w-5 text-orange-600"
                >
                  <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
                </svg>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-orange-600">{stats.totalThreads}</div>
              <p className="text-sm text-slate-500 mt-1">
                All tracked threads
              </p>
            </CardContent>
          </Card>

          <Card className="yb-stats-card border-l-4 border-l-red-500">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-700">Active Threads</CardTitle>
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  className="h-5 w-5 text-red-600"
                >
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12,6 12,12 16,14"/>
                </svg>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-600">{stats.activeThreads}</div>
              <p className="text-sm text-slate-500 mt-1">
                Requiring attention
              </p>
            </CardContent>
          </Card>

          <Card className="yb-stats-card border-l-4 border-l-blue-500">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-700">Channels</CardTitle>
              <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  className="h-5 w-5 text-blue-600"
                >
                  <path d="M7 3a4 4 0 0 1 4 4v8a4 4 0 0 1-4 4 4 4 0 0 1-4-4V7a4 4 0 0 1 4-4z"/>
                  <path d="M20 9v6"/>
                  <path d="M17 7v10"/>
                </svg>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-600">{stats.channels}</div>
              <p className="text-sm text-slate-500 mt-1">
                Being monitored
              </p>
            </CardContent>
          </Card>

          <Card className="yb-stats-card border-l-4 border-l-purple-500">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-700">AI Analyzed</CardTitle>
              <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  className="h-5 w-5 text-purple-600"
                >
                  <circle cx="12" cy="12" r="10"/>
                  <path d="m9 12 2 2 4-4"/>
                </svg>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-purple-600">{stats.aiAnalyzed}</div>
              <p className="text-sm text-slate-500 mt-1">
                Smart insights generated
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Channels List */}
        <Card className="bg-white border border-slate-200 shadow-xl">
          <CardHeader className="bg-slate-50 rounded-t-lg">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-2xl font-bold text-slate-800">Slack Channels</CardTitle>
                <CardDescription className="text-slate-600 mt-1">
                  Click on a channel to view its threads and activity
                </CardDescription>
              </div>
              <Button 
                onClick={fetchChannelData}
                className="yb-button-primary"
                size="sm"
              >
                🔄 Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {channels.length === 0 ? (
                <div className="col-span-full text-center py-12">
                  <div className="w-20 h-20 bg-slate-100 rounded-full mx-auto mb-4 flex items-center justify-center">
                    <svg
                      className="h-10 w-10 text-blue-500"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                      />
                    </svg>
                  </div>
                  <p className="font-semibold text-slate-700 text-lg">No channels found</p>
                  <p className="text-slate-500 mt-1">Start monitoring channels to see them here!</p>
                </div>
              ) : (
                channels.map((channel, index) => (
                  <Card 
                    key={index} 
                    className="cursor-pointer bg-white border border-slate-200 shadow-lg"
                    onClick={() => handleChannelSelect(channel)}
                  >
                    <CardHeader className="pb-3">
                      <CardTitle className="text-lg flex items-center space-x-3">
                        <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                          <span className="text-white font-bold text-sm">#</span>
                        </div>
                        <span className="text-slate-800 font-semibold">{channel.channel_name}</span>
                      </CardTitle>
                      <CardDescription className="text-sm text-slate-500 ml-11">
                        Last activity: {formatTimeAgo(channel.last_activity)}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-slate-600 font-medium">Total Threads:</span>
                          <Badge 
                            variant="secondary" 
                            className="bg-blue-100 text-blue-800"
                          >
                            {channel.thread_count}
                          </Badge>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-slate-600 font-medium">Active:</span>
                          <Badge 
                            variant={channel.active_thread_count > 0 ? "warning" : "success"}
                            className={channel.active_thread_count > 0 
                                                          ? "bg-orange-100 text-orange-800"
                            : "bg-green-100 text-green-800"
                            }
                          >
                            {channel.active_thread_count}
                          </Badge>
                        </div>
                        <div className="pt-2 border-t border-slate-200">
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="w-full text-blue-600 font-medium"
                          >
                            View Threads →
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Recent Threads with Stakeholders */}
        {recentThreads.length > 0 && (
          <Card className="bg-white/70 backdrop-blur-sm border border-slate-200 shadow-xl">
            <CardHeader className="bg-purple-50 rounded-t-lg">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl font-bold text-slate-800">Recent Threads</CardTitle>
                  <CardDescription className="text-slate-600 mt-1">
                    Latest activity across all channels with stakeholder information
                  </CardDescription>
                </div>
                <Button 
                  onClick={fetchChannelData}
                  className="yb-button-primary"
                  size="sm"
                >
                  🔄 Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              <div className="space-y-4">
                {recentThreads.map((thread, index) => (
                  <div key={index} className="bg-white border border-slate-200 rounded-xl p-4">
                    <div className="flex items-start justify-between space-x-4">
                      <div className="flex-1 space-y-3">
                        <div className="flex items-center space-x-3 flex-wrap">
                          <h3 className="font-bold text-lg text-slate-800">
                            {thread.ai_thread_name || 'Thread Discussion'}
                          </h3>
                          {getPriorityBadge(thread.priority)}
                          <Badge className="bg-blue-100 text-blue-800 border border-blue-300">
                            #{thread.channel_name}
                          </Badge>
                        </div>
                        
                        <p className="text-slate-600">
                          {thread.ai_description || 'No description available'}
                        </p>
                        
                        <div className="flex items-center space-x-4 text-sm text-slate-500">
                          <span>{thread.reply_count} replies</span>
                          <span>Last: {formatTimeAgo(thread.latest_reply)}</span>
                        </div>
                        
                        {/* Stakeholders Section */}
                        {thread.ai_stakeholders && parseStakeholders(thread.ai_stakeholders).length > 0 && (
                                                      <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                            <div className="flex items-center space-x-2">
                              <span className="text-sm font-medium text-slate-700">👥 Stakeholders:</span>
                              <Stakeholders 
                                stakeholderIds={parseStakeholders(thread.ai_stakeholders)}
                                maxVisible={5}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                      
                      <div className="flex flex-col space-y-2">
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
                        <Button 
                          onClick={() => {
                            const channelData = channels.find(c => c.channel_name === thread.channel_name)
                            if (channelData) {
                              handleChannelSelect(channelData)
                            }
                          }}
                          className="yb-button-primary text-sm"
                          size="sm"
                        >
                          View Threads →
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

export default ChannelList 