import React, { useState } from 'react'
import SlackIcon from './SlackIcon'
import { Button } from './ui/button'

const SlackLinks = ({ channelId, threadTs, channelName }) => {
  const [showDropdown, setShowDropdown] = useState(false)
  
  // Get team ID from environment or use a fallback
  const teamId = ""
  
  // Generate Slack URLs
  const slackWebUrl = teamId 
    ? `https://app.slack.com/client/${teamId}/${channelId}/thread/${channelId}-${threadTs}`
    : `https://slack.com/app_redirect?channel=${channelId}&message_ts=${threadTs}`
  
  const slackAppUrl = teamId
    ? `slack://channel?team=${teamId}&id=${channelId}&message=${threadTs}`
    : `slack://open?team=${channelId}&id=${channelId}`
  
  const handleSlackWebClick = () => {
    window.open(slackWebUrl, '_blank')
    setShowDropdown(false)
  }
  
  const handleSlackAppClick = () => {
    window.location.href = slackAppUrl
    setShowDropdown(false)
  }
  
  return (
    <div className="relative">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center space-x-1 border-slack-purple/20"
      >
        <SlackIcon className="w-4 h-4" />
        <span className="text-xs">Open in Slack</span>
      </Button>
      
      {showDropdown && (
        <div className="absolute top-full right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 min-w-[160px]">
          <div className="p-2 space-y-1">
            <button
              onClick={handleSlackWebClick}
              className="w-full text-left px-3 py-2 text-sm rounded flex items-center space-x-2"
            >
              <SlackIcon className="w-4 h-4" />
              <span>Open in Browser</span>
            </button>
            <button
              onClick={handleSlackAppClick}
              className="w-full text-left px-3 py-2 text-sm rounded flex items-center space-x-2"
            >
              <SlackIcon className="w-4 h-4" />
              <span>Open in App</span>
            </button>
          </div>
          <div className="border-t border-gray-200 p-2">
            <div className="text-xs text-gray-500 px-3 py-1">
              #{channelName}
            </div>
            {!teamId && (
              <div className="text-xs text-orange-600 px-3 py-1">
                Set REACT_APP_SLACK_TEAM_ID for direct links
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Click outside to close dropdown */}
      {showDropdown && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setShowDropdown(false)}
        />
      )}
    </div>
  )
}

export default SlackLinks 