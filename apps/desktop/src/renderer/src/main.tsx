import './styles.css'
import '@minidrive/ui/src/styles.css'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

for (const type of ['dragover', 'drop']) {
  document.addEventListener(type, (e) => e.preventDefault())
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
