import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import Dashboard from './components/Dashboard';
import ThreadDetails from './components/ThreadDetails';

function App() {
  return (
    <Router>
      <div className="App min-h-screen bg-gray-950">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/thread/:threadId" element={<ThreadDetails />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
