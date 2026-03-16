import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Analysis from './pages/Analysis'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Analysis />} />
      </Routes>
    </Layout>
  )
}

export default App
