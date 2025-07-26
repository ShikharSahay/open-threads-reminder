import React, { useState, useEffect } from 'react'
import { Button } from './ui/button'

const Stakeholders = ({ stakeholderIds, maxVisible = 3 }) => {
  const [profiles, setProfiles] = useState([])
  const [expanded, setExpanded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [hoveredUser, setHoveredUser] = useState(null)

  useEffect(() => {
    const parsedIds = parseStakeholderIds(stakeholderIds)
    if (parsedIds && parsedIds.length > 0) {
      fetchUserProfiles(parsedIds)
    }
  }, [stakeholderIds])

  const fetchUserProfiles = async (userIds) => {
    if (!userIds || userIds.length === 0) return
    
    try {
      setLoading(true)
      const userIdsParam = userIds.join(',')
      const response = await fetch(`/api/user-profiles?user_ids=${encodeURIComponent(userIdsParam)}`)
      
      if (response.ok) {
        const profilesData = await response.json()
        setProfiles(profilesData || [])
      } else {
        console.error('Failed to fetch user profiles:', response.status)
        setProfiles([])
      }
    } catch (error) {
      console.error('Error fetching user profiles:', error)
      setProfiles([])
    } finally {
      setLoading(false)
    }
  }

  // Parse stakeholder IDs from string if needed
  const parseStakeholderIds = (stakeholders) => {
    if (!stakeholders) return []
    if (Array.isArray(stakeholders)) return stakeholders
    
    // Handle comma-separated string
    if (typeof stakeholders === 'string') {
      return stakeholders.split(',').map(id => id.trim()).filter(id => id.length > 0)
    }
    
    return []
  }

  const parsedStakeholderIds = parseStakeholderIds(stakeholderIds)
  
  if (!parsedStakeholderIds || parsedStakeholderIds.length === 0) {
    return (
      <span className="text-xs text-slate-400">No stakeholders</span>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center space-x-2">
        <div className="animate-pulse flex space-x-1">
          {[1, 2, 3].map(i => (
            <div key={i} className="w-8 h-8 bg-slate-200 rounded-full"></div>
          ))}
        </div>
        <span className="text-sm text-slate-500">Loading stakeholders...</span>
      </div>
    )
  }

  const visibleProfiles = expanded ? profiles : profiles.slice(0, maxVisible)
  const remainingCount = profiles.length - maxVisible

  const ProfilePicture = ({ profile, index }) => (
    <div
      key={profile.user_id}
      className="relative"
      onMouseEnter={() => setHoveredUser(profile.user_id)}
      onMouseLeave={() => setHoveredUser(null)}
    >
      <div 
        className="w-8 h-8 rounded-full border-2 border-white shadow-lg cursor-pointer"
        style={{ zIndex: profiles.length - index }}
      >
        <img
          src={profile.profile_image_32 || profile.profile_image_24 || '/api/placeholder/32/32'}
          alt={profile.display_name || profile.real_name || profile.name}
          className="w-full h-full rounded-full object-cover"
          onError={(e) => {
            e.target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(profile.display_name || profile.name)}&background=f97316&color=fff&size=32`
          }}
        />
      </div>
      
      {/* Tooltip */}
      {hoveredUser === profile.user_id && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 z-50">
          <div className="bg-slate-800 text-white text-xs rounded-lg px-3 py-2 shadow-xl whitespace-nowrap">
            <div className="font-semibold">{profile.display_name || profile.real_name || profile.name}</div>
            <div className="text-slate-300">@{profile.name}</div>
            <div className="text-slate-400 text-xs">{profile.user_id}</div>
            {/* Arrow */}
            <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-slate-800"></div>
          </div>
        </div>
      )}
    </div>
  )

  return (
    <div className="flex items-center space-x-2">
      <div className="flex items-center">
        {visibleProfiles.map((profile, index) => (
          <div
            key={profile.user_id}
            className={index > 0 ? "-ml-2" : ""}
          >
            <ProfilePicture profile={profile} index={index} />
          </div>
        ))}
        
        {!expanded && remainingCount > 0 && (
          <div className="-ml-2">
            <div 
              className="w-8 h-8 rounded-full bg-orange-500 border-2 border-white shadow-lg flex items-center justify-center cursor-pointer"
              onClick={() => setExpanded(true)}
            >
              <span className="text-white text-xs font-bold">+{remainingCount}</span>
            </div>
          </div>
        )}
      </div>
      
      {expanded && remainingCount > 0 && (
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={() => setExpanded(false)}
                          className="text-xs text-slate-500 p-1 h-auto"
        >
          Show less
        </Button>
      )}
      
      <div className="text-xs text-slate-500">
        {profiles.length === 1 ? '1 stakeholder' : `${profiles.length} stakeholders`}
      </div>
    </div>
  )
}

export default Stakeholders 