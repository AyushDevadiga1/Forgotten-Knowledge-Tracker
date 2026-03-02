import { BrowserRouter, Routes, Route } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import OverviewPage from './pages/OverviewPage'
import ReviewPage from './pages/ReviewPage'
import KnowledgeBasePage from './pages/KnowledgeBasePage'
import AddConceptPage from './pages/AddConceptPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="review" element={<ReviewPage />} />
          <Route path="database" element={<KnowledgeBasePage />} />
          <Route path="add" element={<AddConceptPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
