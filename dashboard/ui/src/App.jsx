import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import ChannelList from './components/ChannelList'
import ChannelThreads from './components/ChannelThreads'
import './index.css'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ChannelList />} />
        <Route path="/channels" element={<ChannelList />} />
        <Route path="/channels/:channelId/threads" element={<ChannelThreads />} />
      </Routes>
    </Router>
  )
}

export default App 