import React, { createContext, useContext, useState, useEffect } from 'react';
import api, { setAuthData, clearAuthData, getStoredUser } from '../utils/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in on mount
    const storedUser = getStoredUser();
    const token = localStorage.getItem('token');
    if (storedUser && token) {
      setUser(storedUser);
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    try {
      const response = await api.post('/auth/login', { email, password });
      const { access_token, user: userData } = response.data;
      
      setAuthData(access_token, userData);
      setUser(userData);
      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      const message = error.response?.data?.detail || 'Invalid email or password.';
      return { success: false, error: message };
    }
  };

  const register = async (userData) => {
    try {
      await api.post('/auth/register', userData);
      return { success: true };
    } catch (error) {
      console.error('Registration error:', error);
      const message = error.response?.data?.detail || 'Registration failed. Try again.';
      return { success: false, error: message };
    }
  };

  const logout = () => {
    clearAuthData();
    setUser(null);
  };

  const updateProfile = (updatedFields) => {
    setUser((prev) => {
      const newProfile = { ...prev, ...updatedFields };
      localStorage.setItem('user', JSON.stringify(newProfile));
      return newProfile;
    });
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, updateProfile }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
