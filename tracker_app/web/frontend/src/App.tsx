import { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { LazyMotion, domMax } from 'motion/react'
import MainLayout from './layouts/MainLayout'
import OverviewPage from './pages/OverviewPage'
import ReviewPage from './pages/ReviewPage'
import KnowledgeBasePage from './pages/KnowledgeBasePage'
import AddConceptPage from './pages/AddConceptPage'
import QuizPage from './pages/QuizPage'
import { GraphSkeleton } from './components/PageSkeleton'
import { SessionProvider } from './context/SessionContext'

// anime.js (force-graph settling) is the heaviest optional dep — it and the
// graph page load only when /graph is visited, keeping the initial bundle lean.
const GraphPage = lazy(() => import('./pages/GraphPage'))

// domMax (not domAnimation) is required because the shell's shared-element
// nav pill uses layoutId — a layout-animation feature that domAnimation does
// not include. LazyMotion still lazy-loads the feature bundles and keeps every
// page on the single `m` component API.
function App() {
  return (
    <LazyMotion features={domMax}>
      <BrowserRouter>
        <SessionProvider>
          <Suspense fallback={<GraphSkeleton />}>
            <Routes>
              <Route path="/" element={<MainLayout />}>
                <Route index element={<OverviewPage />} />
                <Route path="review" element={<ReviewPage />} />
                <Route path="database" element={<KnowledgeBasePage />} />
                <Route path="add" element={<AddConceptPage />} />
                <Route path="graph" element={<GraphPage />} />
                <Route path="quiz" element={<QuizPage />} />
              </Route>
            </Routes>
          </Suspense>
        </SessionProvider>
      </BrowserRouter>
    </LazyMotion>
  )
}

export default App
