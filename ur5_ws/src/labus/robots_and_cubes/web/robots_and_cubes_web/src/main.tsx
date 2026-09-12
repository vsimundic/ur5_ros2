import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { KidApp } from './KidApp';
import { OperatorApp } from './OperatorApp';
import './styles.css';

const App = location.pathname.startsWith('/operator') ? OperatorApp : KidApp;
createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
