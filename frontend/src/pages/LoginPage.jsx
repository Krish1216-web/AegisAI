import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Lock, User, Eye, EyeOff, AlertCircle, Sparkles, UserCheck, ShieldAlert, Mail, ArrowLeft, CheckCircle2, RotateCw } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const { login, register } = useAuth();
  const [formType, setFormType] = useState('login'); // 'login', 'register', 'forgot', 'reset'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState('');
  const navigate = useNavigate();

  const handleVerify = async (name, pass) => {
    setIsLoading(true);
    setLoadingStep('Securing root token key rings...');
    try {
      const profile = await login(name, pass);
      const userRole = profile.role.name.toLowerCase();
      if (userRole === 'admin' || userRole === 'super admin') {
        navigate('/admin/dashboard');
      } else {
        navigate('/user/dashboard');
      }
    } catch (err) {
      setError(err.message || 'Decryption failure: Invalid identity credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoginSubmit = (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (!username || !password) {
      setError('Credentials incomplete. Authenticate all fields.');
      return;
    }
    handleVerify(username, password);
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (!username || !email || !password) {
      setError('Registration incomplete. All node parameters required.');
      return;
    }
    setIsLoading(true);
    setLoadingStep('Generating security handshake certificates...');
    try {
      await register(username, email, password);
      setSuccess('Handshake registered! Decrypt using your credentials.');
      setFormType('login');
    } catch (err) {
      setError(err.message || 'Registration failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotSubmit = (e) => {
    e.preventDefault();
    setError('');
    if (!email) {
      setError('Email identifier required.');
      return;
    }
    setIsLoading(true);
    setLoadingStep('Dispatching recovery decrypt token...');
    setTimeout(() => {
      setSuccess('Verification security token dispatched to email.');
      setFormType('reset');
      setIsLoading(false);
    }, 1500);
  };

  const handleResetSubmit = (e) => {
    e.preventDefault();
    setError('');
    if (!newPassword) {
      setError('New security key required.');
      return;
    }
    setIsLoading(true);
    setLoadingStep('Overwriting database key rings...');
    setTimeout(() => {
      setSuccess('Security key updated. Log in using your new key.');
      setFormType('login');
      setIsLoading(false);
    }, 1500);
  };

  // Quick demonstration shortcut logins
  const handleQuickLogin = (role) => {
    setError('');
    setSuccess('');
    if (role === 'super') {
      setUsername('superadmin');
      setPassword('super2026');
      handleVerify('superadmin', 'super2026');
    } else if (role === 'admin') {
      setUsername('admin');
      setPassword('admin2026');
      handleVerify('admin', 'admin2026');
    } else {
      setUsername('user');
      setPassword('user2026');
      handleVerify('user', 'user2026');
    }
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      padding: '20px',
      background: 'radial-gradient(circle at center, #11131c 0%, #06070a 100%)',
      position: 'relative',
      overflow: 'hidden'
    }} className="scanline">
      
      {/* Decorative glows */}
      <div style={{ position: 'absolute', width: '350px', height: '350px', borderRadius: '50%', background: 'rgba(189, 0, 255, 0.04)', filter: 'blur(90px)', top: '15%', left: '15%' }}></div>
      <div style={{ position: 'absolute', width: '350px', height: '350px', borderRadius: '50%', background: 'rgba(0, 240, 255, 0.04)', filter: 'blur(90px)', bottom: '15%', right: '15%' }}></div>

      <div className="glass-panel" style={{
        width: '100%',
        maxWidth: '430px',
        padding: '36px 28px',
        border: '1px solid rgba(0, 240, 255, 0.15)',
        boxShadow: '0 0 35px rgba(0, 240, 255, 0.06)',
        borderRadius: '16px',
        position: 'relative',
        zIndex: 10,
        textAlign: 'center'
      }}>
        
        {/* Shield Icon Header */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px' }}>
          <div className="flex-center" style={{
            width: '56px',
            height: '56px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, rgba(0, 240, 255, 0.2), rgba(189, 0, 255, 0.2))',
            border: '1px solid rgba(0, 240, 255, 0.4)',
            boxShadow: '0 0 15px rgba(0, 240, 255, 0.1)'
          }}>
            <Shield size={28} style={{ color: 'var(--color-neon-cyan)', filter: 'drop-shadow(0 0 4px rgba(0, 240, 255, 0.4))' }} />
          </div>
        </div>

        {/* Branding Title */}
        <h2 style={{ fontSize: '1.6rem', fontWeight: 700, marginBottom: '6px', letterSpacing: '0.05em' }}>
          AEGIS<span className="gradient-text">AI</span> SECURITY
        </h2>
        
        {/* Status Notification Alerts */}
        {error && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px', borderRadius: '6px', backgroundColor: 'rgba(255, 0, 127, 0.05)', border: '1px solid rgba(255, 0, 127, 0.2)', color: 'var(--color-neon-pink)', fontSize: '0.75rem', textAlign: 'left', marginBottom: '16px' }}>
            <AlertCircle size={14} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px', borderRadius: '6px', backgroundColor: 'rgba(0, 255, 170, 0.05)', border: '1px solid rgba(0, 255, 170, 0.2)', color: 'var(--color-neon-green)', fontSize: '0.75rem', textAlign: 'left', marginBottom: '16px' }}>
            <CheckCircle2 size={14} style={{ flexShrink: 0 }} />
            <span>{success}</span>
          </div>
        )}

        {isLoading ? (
          /* Loading display states */
          <div style={{ padding: '24px 0', minHeight: '180px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ width: '36px', height: '36px', border: '3px solid rgba(0, 240, 255, 0.1)', borderTopColor: 'var(--color-neon-cyan)', borderRadius: '50%', animation: 'spinSlow 1.2s infinite linear', marginBottom: '16px' }}></div>
            <div style={{ fontSize: '0.85rem', color: 'var(--color-neon-cyan)', fontFamily: 'var(--font-mono)' }}>{loadingStep}</div>
          </div>
        ) : (
          /* Authentication sub-forms container toggler */
          <React.Fragment>
            {formType === 'login' && (
              <form onSubmit={handleLoginSubmit} style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '12px', textAlign: 'center' }}>
                  Secure Authentication Node. Enter credentials.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Node Identity ID</label>
                  <div style={{ position: 'relative' }}>
                    <User size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
                    <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="admin, user, or superadmin" className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-2.5 pl-10 pr-4 text-xs text-white w-full outline-none focus:border-cyan-500/50 transition-all" />
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <label style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Access key code</label>
                    <button type="button" onClick={() => setFormType('forgot')} style={{ background: 'transparent', border: 'none', color: 'var(--color-neon-cyan)', fontSize: '0.7rem', cursor: 'pointer' }} className="hover:underline">Forgot Key?</button>
                  </div>
                  <div style={{ position: 'relative' }}>
                    <Lock size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
                    <input type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="security-key password" className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-2.5 pl-10 pr-10 text-xs text-white w-full outline-none focus:border-cyan-500/50 transition-all" />
                    <button type="button" onClick={() => setShowPassword(!showPassword)} style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer' }}>{showPassword ? <EyeOff size={14} /> : <Eye size={14} />}</button>
                  </div>
                </div>

                <button type="submit" className="btn-primary py-2.5 rounded-lg text-xs mt-2 justify-center"><Sparkles size={14} /> DECRYPT_NODE</button>
                <div style={{ textAlign: 'center', fontSize: '0.75rem', marginTop: '8px' }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>New Operator? </span>
                  <button type="button" onClick={() => setFormType('register')} style={{ background: 'transparent', border: 'none', color: 'var(--color-neon-cyan)', cursor: 'pointer', fontWeight: 600 }}>Register Node</button>
                </div>
              </form>
            )}

            {formType === 'register' && (
              <form onSubmit={handleRegisterSubmit} style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '12px', textAlign: 'center' }}>Create a new system identity node.</p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>Handle Name</label>
                  <div style={{ position: 'relative' }}>
                    <User size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
                    <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-2.5 pl-10 pr-4 text-xs text-white w-full outline-none focus:border-cyan-500/50" />
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>Email Address</label>
                  <div style={{ position: 'relative' }}>
                    <Mail size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
                    <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email@address.com" className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-2.5 pl-10 pr-4 text-xs text-white w-full outline-none focus:border-cyan-500/50" />
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>Security key</label>
                  <div style={{ position: 'relative' }}>
                    <Lock size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
                    <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-2.5 pl-10 pr-4 text-xs text-white w-full outline-none focus:border-cyan-500/50" />
                  </div>
                </div>

                <button type="submit" className="btn-primary py-2.5 rounded-lg text-xs mt-2 justify-center">REGISTER_NODE</button>
                
                <button type="button" onClick={() => setFormType('login')} style={{ background: 'transparent', border: 'none', color: 'var(--color-text-secondary)', fontSize: '0.75rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', alignSelf: 'center', marginTop: '8px' }}>
                  <ArrowLeft size={12} /> Back to Decryption
                </button>
              </form>
            )}

            {formType === 'forgot' && (
              <form onSubmit={handleForgotSubmit} style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '12px', textAlign: 'center' }}>Recover your access credentials node key.</p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>Registered Email</label>
                  <div style={{ position: 'relative' }}>
                    <Mail size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
                    <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email@address.com" className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-2.5 pl-10 pr-4 text-xs text-white w-full outline-none focus:border-cyan-500/50" />
                  </div>
                </div>

                <button type="submit" className="btn-primary py-2.5 rounded-lg text-xs mt-2 justify-center">DISPATCH_TOKEN</button>
                
                <button type="button" onClick={() => setFormType('login')} style={{ background: 'transparent', border: 'none', color: 'var(--color-text-secondary)', fontSize: '0.75rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', alignSelf: 'center', marginTop: '8px' }}>
                  <ArrowLeft size={12} /> Back to Decryption
                </button>
              </form>
            )}

            {formType === 'reset' && (
              <form onSubmit={handleResetSubmit} style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', marginBottom: '12px', textAlign: 'center' }}>Overwriting access keys.</p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>New Decryption key</label>
                  <div style={{ position: 'relative' }}>
                    <Lock size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
                    <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="new password" className="bg-white/3 border border-[rgba(255,255,255,0.06)] rounded-lg py-2.5 pl-10 pr-4 text-xs text-white w-full outline-none focus:border-cyan-500/50" />
                  </div>
                </div>

                <button type="submit" className="btn-primary py-2.5 rounded-lg text-xs mt-2 justify-center">UPDATE_KEY_RINGS</button>
              </form>
            )}
          </React.Fragment>
        )}

        {/* Separator for shortcuts */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: '24px 0 16px', color: 'var(--color-text-muted)', fontSize: '0.7rem' }}>
          <div style={{ flex: 1, height: '1px', backgroundColor: 'rgba(255,255,255,0.04)' }}></div>
          <span>ROLE-BASED DEMO SHORTCUTS</span>
          <div style={{ flex: 1, height: '1px', backgroundColor: 'rgba(255,255,255,0.04)' }}></div>
        </div>

        {/* Demo shortcuts */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
          <button onClick={() => handleQuickLogin('user')} className="btn-secondary py-1.5 px-3 rounded-lg text-[10px] gap-1 hover:border-cyan-500/30">
            <UserCheck size={10} className="text-cyan-400" /> User Portal
          </button>
          <button onClick={() => handleQuickLogin('admin')} className="btn-secondary py-1.5 px-3 rounded-lg text-[10px] gap-1 hover:border-purple-500/30">
            <ShieldAlert size={10} className="text-purple-400" /> Admin
          </button>
          <button onClick={() => handleQuickLogin('super')} className="btn-secondary py-1.5 px-3 rounded-lg text-[10px] gap-1 hover:border-rose-500/30">
            <Shield size={10} className="text-rose-400" /> Super Admin
          </button>
        </div>

        {/* Credentials table footer */}
        <div style={{ marginTop: '24px', padding: '10px', borderRadius: '6px', backgroundColor: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', fontSize: '0.65rem', color: 'var(--color-text-muted)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', textAlign: 'left' }}>
          <span>User: <code style={{ color: 'var(--color-neon-cyan)' }}>user</code> / <code style={{ color: 'var(--color-neon-cyan)' }}>user2026</code></span>
          <span>Admin: <code style={{ color: 'var(--color-neon-purple)' }}>admin</code> / <code style={{ color: 'var(--color-neon-purple)' }}>admin2026</code></span>
          <span style={{ gridColumn: 'span 2' }}>Super Admin: <code style={{ color: 'var(--color-neon-pink)' }}>superadmin</code> / <code style={{ color: 'var(--color-neon-pink)' }}>super2026</code></span>
        </div>

      </div>
    </div>
  );
}
