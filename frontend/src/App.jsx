import { useState, useEffect } from 'react';
import { getStores, createStore, deleteStore } from './api';
import { Plus, Trash2, ExternalLink, RefreshCw, AlertCircle, ShoppingBag } from 'lucide-react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

function App() {
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newStoreName, setNewStoreName] = useState('');
  const [newStoreType, setNewStoreType] = useState('woocommerce');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  const fetchStores = async () => {
    setLoading(true);
    try {
      const data = await getStores();
      setStores(data);
      setError(null);

    } catch (err) {
      console.error("Failed to fetch stores", err);
      setError("Failed to fetch stores");
      alert("Failed to fetch stores");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStores();
  }, []);

  const handleCreateStore = async (e) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    setIsModalOpen(false);
    try {
      await createStore(newStoreName, newStoreType);
      setNewStoreName('');
      setNewStoreType('woocommerce');
      fetchStores();
    } catch (err) {
      const msg = err.response?.data?.detail || "Failed to create store";
      setError(msg);
      alert(msg);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteStore = async (name) => {
    if (!confirm(`Are you sure you want to delete store "${name}"? This action cannot be undone.`)) return;
    try {
      await deleteStore(name);
      fetchStores(); // Refresh immediately to show "Deleting" status
    } catch (err) {
      alert("Failed to delete store: " + (err.response?.data?.detail || err.message));
    }
  };

  const getStatusBadge = (status, errorMsg) => {
    switch (status) {
      case 'Ready':
        return <span className="px-2 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800">Ready</span>;
      case 'Provisioning':
        return <span className="px-2 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 animate-pulse">Provisioning...</span>;
      case 'Starting':
        return <span className="px-2 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800 animate-pulse">Starting...</span>;
      case 'Deleting':
        return <span className="px-2 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-800 animate-pulse">Deleting...</span>;
      case 'Failed':
        return (
          <div className="flex flex-col items-start gap-1">
            <span className="px-2 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800">Failed</span>
            {errorMsg && <span className="text-[10px] text-red-600 max-w-[200px] leading-tight">{errorMsg}</span>}
          </div>
        );
      default:
        return <span className="px-2 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-800">{status}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShoppingBag className="w-6 h-6 text-indigo-600" />
            <h1 className="text-xl font-bold text-gray-900">Urumi Store Platform</h1>
          </div>
          <button 
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create New Store
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Stats / Context */}
        <div className="mb-6 flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-700">Your Stores</h2>
            <button onClick={fetchStores} disabled={loading} className="text-gray-500 hover:text-indigo-600 transition-colors p-2 rounded-full hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed" title="Refresh">
                <RefreshCw className={cn("w-5 h-5", loading && "animate-spin")} />
            </button>
        </div>

        {/* Global Error */}
        {error && (
            <div className="mb-6 bg-red-50 border-l-4 border-red-500 p-4 rounded-md">
                <div className="flex items-center">
                    <AlertCircle className="w-5 h-5 text-red-500 mr-2" />
                    <p className="text-sm text-red-700">{error}</p>
                </div>
            </div>
        )}

        {/* Store Grid/List */}
        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          {stores.length === 0 && !loading ? (
             <div className="text-center py-12">
                <ShoppingBag className="mx-auto h-12 w-12 text-gray-300" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No stores yet</h3>
                <p className="mt-1 text-sm text-gray-500">Get started by creating a new store.</p>
                <div className="mt-6">
                <button
                    onClick={() => setIsModalOpen(true)}
                    className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                    <Plus className="-ml-1 mr-2 h-5 w-5" aria-hidden="true" />
                    Create Store
                </button>
                </div>
            </div>
          ) : (
            <ul className="divide-y divide-gray-200">
              {stores.map((store) => (
                <li key={store.id} className="hover:bg-gray-50 transition-colors">
                  <div className="px-4 py-4 sm:px-6">
                    <div className="flex items-center justify-between">
                      <div className="flex flex-col">
                        <div className="flex items-center gap-3">
                            <p className="text-md font-medium text-indigo-600 truncate">{store.name}</p>
                            {getStatusBadge(store.status, store.error_message)}
                        </div>
                        <p className="mt-1 flex items-center text-sm text-gray-500">
                            Type: <span className="capitalize ml-1 font-medium">{store.type}</span>
                            <span className="mx-2 text-gray-300">|</span>
                            Created: {new Date(store.created_at).toLocaleString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-4">
                        {store.url && store.status === 'Ready' && (
                            <a 
                                href={store.url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-indigo-600 transition-colors"
                            >
                                <ExternalLink className="w-4 h-4" />
                                Visit Store
                            </a>
                        )}
                        <button 
                            onClick={() => handleDeleteStore(store.name)}
                            disabled={store.status === 'Deleting'}
                            className="text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed p-2 rounded-full hover:bg-white"
                            title="Delete Store"
                        >
                            <Trash2 className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>

      {/* Create Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 animate-in fade-in zoom-in duration-200">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Create New Store</h2>
            <form onSubmit={handleCreateStore}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Store Name</label>
                  <input
                    type="text"
                    required
                    pattern="[a-z0-9-]+"
                    title="Lowercase letters, numbers, and hyphens only"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2 border"
                    placeholder="my-cool-store"
                    value={newStoreName}
                    onChange={(e) => setNewStoreName(e.target.value)}
                  />
                  <p className="mt-1 text-xs text-gray-500">Lowercase, numbers, hyphens only.</p>
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-700">Store Type</label>
                    <div className="mt-1 grid grid-cols-2 gap-3">
                        <button
                            type="button"
                            onClick={() => setNewStoreType('woocommerce')}
                            className={cn(
                                "border rounded-md py-3 px-4 flex items-center justify-center text-sm font-medium transition-all hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500",
                                newStoreType === 'woocommerce' 
                                    ? "border-indigo-600 ring-1 ring-indigo-600 bg-indigo-50 text-indigo-700"
                                    : "border-gray-300 text-gray-700 bg-white"
                            )}
                        >
                            WooCommerce
                        </button>
                        <button
                            type="button"
                            onClick={() => setNewStoreType('medusa')}
                            className={cn(
                                "border rounded-md py-3 px-4 flex items-center justify-center text-sm font-medium transition-all hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500",
                                newStoreType === 'medusa' 
                                    ? "border-indigo-600 ring-1 ring-indigo-600 bg-indigo-50 text-indigo-700"
                                    : "border-gray-300 text-gray-700 bg-white"
                            )}
                        >
                            Medusa
                        </button>
                    </div>
                </div>
              </div>
              <div className="mt-6 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-70 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {creating && <RefreshCw className="w-4 h-4 animate-spin" />}
                  {creating ? 'Creating...' : 'Create Store'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
