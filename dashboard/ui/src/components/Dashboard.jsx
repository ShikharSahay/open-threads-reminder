import React, { useState } from 'react'
import ChannelList from './ChannelList'
import ChannelThreads from './ChannelThreads'

const Dashboard = () => {
  const [currentView, setCurrentView] = useState('channels') // 'channels' or 'threads'
  const [selectedChannel, setSelectedChannel] = useState(null)

  const handleChannelSelect = (channel) => {
    setSelectedChannel(channel)
    setCurrentView('threads')
  }

  const handleBackToChannels = () => {
    setCurrentView('channels')
    setSelectedChannel(null)
  }

  // Render the appropriate view based on current state
  if (currentView === 'threads' && selectedChannel) {
    return (
      <ChannelThreads 
        channel={selectedChannel}
        onBack={handleBackToChannels}
      />
    )
  }

  // Default to channel list view
  return (
    <ChannelList onChannelSelect={handleChannelSelect} />
  )
}

export default Dashboard 