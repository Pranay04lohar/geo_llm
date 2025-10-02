import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getLastSimple } from '../utils/api';
import { useAlert } from '@/components/AlertProvider';

const QuotaDisplay = () => {
  const { user } = useAuth();
  const { showError } = useAlert();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getLastSimple();
        if (!cancelled) setData(res);
      } catch (err) {
        if (!cancelled) setError(err.message);
        if (err.message?.toLowerCase().includes('unauthorized')) {
          showError('Unauthorized', 'Please sign in to view your latest retrieval results.');
        } else {
          showError('Error', err.message || 'Failed to load data.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    if (user) run();
    return () => { cancelled = true; };
  }, [user, showError]);

  if (!user) return null;

  if (loading) return <div className="text-sm text-gray-500">Loading...</div>;
  if (error) return <div className="text-sm text-red-600">{error}</div>;

  return (
    <div className="text-sm text-gray-700">
      {data ? 'Latest retrieval ready.' : 'No retrieval yet.'}
    </div>
  );
};

export default QuotaDisplay;

 