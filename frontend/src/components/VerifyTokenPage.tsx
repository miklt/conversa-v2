import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './VerifyTokenPage.css';

export function VerifyTokenPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { verifyToken, isLoading } = useAuth();
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    
    if (!token) {
      setStatus('error');
      setErrorMessage('Token não encontrado na URL');
      return;
    }

    const handleVerification = async () => {
      try {
        await verifyToken(token);
        setStatus('success');
        // Redirect to chat after a short delay
        setTimeout(() => {
          navigate('/chat');
        }, 2000);
      } catch (error: any) {
        console.error('Token verification failed:', error);
        setStatus('error');
        setErrorMessage(
          error.response?.data?.detail || 
          'Token inválido ou expirado. Solicite um novo link de acesso.'
        );
      }
    };

    handleVerification();
  }, [searchParams, verifyToken, navigate]);

  const handleRequestNewLink = () => {
    navigate('/');
  };

  if (status === 'verifying' || isLoading) {
    return (
      <div className="verify-page">
        <div className="verify-container">
          <div className="verify-content">
            <div className="loading-spinner"></div>
            <h2>Verificando acesso...</h2>
            <p>Aguarde enquanto verificamos seu link de acesso.</p>
          </div>
        </div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="verify-page">
        <div className="verify-container">
          <div className="verify-content success">
            <div className="success-icon">✅</div>
            <h2>Acesso confirmado!</h2>
            <p>Você será redirecionado para o chat em instantes...</p>
            <div className="success-details">
              <p>Bem-vindo ao sistema Conversa Estágios!</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="verify-page">
        <div className="verify-container">
          <div className="verify-content error">
            <div className="error-icon">❌</div>
            <h2>Erro na verificação</h2>
            <p className="error-message">{errorMessage}</p>
            
            <div className="error-actions">
              <button 
                onClick={handleRequestNewLink}
                className="new-link-button"
              >
                Solicitar Novo Link
              </button>
            </div>
            
            <div className="error-help">
              <h3>Possíveis causas:</h3>
              <ul>
                <li>O link expirou (links são válidos por 15 minutos)</li>
                <li>O link já foi usado anteriormente</li>
                <li>O link está mal formatado</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}