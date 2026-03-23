'use client'

import { useState, useEffect } from 'react'
import { Users, Search, Trash2, Shield, User as UserIcon, Mail, Calendar, AlertCircle, Loader2 } from 'lucide-react'
import api from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'

interface UserAccount {
  id: number
  email: string
  full_name: string
  role: string
  is_active: boolean
  is_verified: boolean
  created_at: string
}

export function UserManagement() {
  const { user: currentUser } = useAuthStore()
  const [users, setUsers] = useState<UserAccount[]>([])
  const [filteredUsers, setFilteredUsers] = useState<UserAccount[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<number | null>(null)
  const [changingRole, setChangingRole] = useState<number | null>(null)
  const [selectedRole, setSelectedRole] = useState<string>('all')

  useEffect(() => {
    fetchUsers()
  }, [])

  useEffect(() => {
    filterUsers()
  }, [users, searchTerm, selectedRole])

  const fetchUsers = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.get('/api/auth/users')
      setUsers(response.data.users || [])
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to fetch users'
      setError(errorMessage)
      console.error('Failed to fetch users:', err)
    } finally {
      setLoading(false)
    }
  }

  const filterUsers = () => {
    let filtered = users

    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      filtered = filtered.filter(
        user =>
          user.email.toLowerCase().includes(term) ||
          user.full_name.toLowerCase().includes(term)
      )
    }

    if (selectedRole !== 'all') {
      filtered = filtered.filter(user => user.role === selectedRole)
    }

    setFilteredUsers(filtered)
  }

  const deleteUser = async (userId: number, userEmail: string) => {
    if (!confirm(`Are you sure you want to delete ${userEmail}? This action cannot be undone.`)) {
      return
    }

    try {
      setDeleting(userId)
      await api.delete(`/api/auth/users/${userId}`)
      setUsers(users.filter(u => u.id !== userId))
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to delete user'
      alert(`Error: ${errorMessage}`)
      console.error('Failed to delete user:', err)
    } finally {
      setDeleting(null)
    }
  }

  const changeRole = async (userId: number, newRole: string) => {
    try {
      setChangingRole(userId)
      const response = await api.put(`/api/auth/users/${userId}/role`, { role: newRole })
      setUsers(prev =>
        prev.map(u => (u.id === userId ? { ...u, role: response.data.user.role } : u))
      )
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to change role'
      alert(`Error: ${errorMessage}`)
      console.error('Failed to change role:', err)
    } finally {
      setChangingRole(null)
    }
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-red-500/20 text-red-400 border border-red-500/30'
      case 'manager':
        return 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
      case 'engineer':
        return 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
      case 'hr':
        return 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
      case 'leader':
        return 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
      default:
        return 'bg-gray-500/20 text-gray-400 border border-gray-500/30'
    }
  }

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'admin':
        return <Shield className="w-3.5 h-3.5" />
      default:
        return <UserIcon className="w-3.5 h-3.5" />
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <div className="h-full flex flex-col overflow-hidden bg-gradient-to-br from-slate-900 via-[#07182D] to-slate-900 p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center space-x-3 mb-2">
          <div className="p-2 bg-gradient-to-br from-cyan-500/20 to-blue-600/20 rounded-lg border border-cyan-500/30">
            <Users className="w-5 h-5 text-cyan-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">User Management</h1>
        </div>
        <p className="text-sm text-gray-400">Manage all registered user accounts</p>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
          <p className="text-xs text-gray-400 mb-1">Total Users</p>
          <p className="text-2xl font-bold text-white">{users.length}</p>
        </div>
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
          <p className="text-xs text-gray-400 mb-1">Active Users</p>
          <p className="text-2xl font-bold text-green-400">{users.filter(u => u.is_active).length}</p>
        </div>
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
          <p className="text-xs text-gray-400 mb-1">Admins</p>
          <p className="text-2xl font-bold text-red-400">{users.filter(u => u.role === 'admin').length}</p>
        </div>
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4">
          <p className="text-xs text-gray-400 mb-1">Verified</p>
          <p className="text-2xl font-bold text-cyan-400">{users.filter(u => u.is_verified).length}</p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center space-x-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search by email or name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-800/50 border border-slate-700/50 rounded-lg pl-10 pr-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500/50 transition-colors text-sm"
          />
        </div>
        <select
          value={selectedRole}
          onChange={(e) => setSelectedRole(e.target.value)}
          className="bg-slate-800/50 border border-slate-700/50 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-cyan-500/50 transition-colors"
        >
          <option value="all">All Roles</option>
          <option value="admin">Admin</option>
          <option value="manager">Manager</option>
          <option value="leader">Leader</option>
          <option value="engineer">Engineer</option>
          <option value="hr">HR</option>
          <option value="employee">Employee</option>
        </select>
        <button
          onClick={fetchUsers}
          className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg hover:from-cyan-400 hover:to-blue-500 transition-all font-medium text-sm shadow-lg shadow-cyan-500/30"
        >
          Refresh
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-400">Error</p>
            <p className="text-xs text-red-400/80">{error}</p>
          </div>
        </div>
      )}

      {/* Users Table */}
      <div className="flex-1 overflow-y-auto rounded-lg border border-slate-700/50 bg-slate-800/30 backdrop-blur-sm">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-cyan-400 animate-spin mx-auto mb-2" />
              <p className="text-gray-400 text-sm">Loading users...</p>
            </div>
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <Users className="w-8 h-8 text-gray-600 mx-auto mb-2" />
              <p className="text-gray-400 text-sm">
                {users.length === 0 ? 'No users found' : 'No users match your search'}
              </p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-slate-700/30">
            {/* Table Header */}
            <div className="hidden md:grid md:grid-cols-12 gap-4 px-6 py-3 bg-slate-800/50 border-b border-slate-700/30 sticky top-0 text-xs font-semibold text-gray-300 uppercase tracking-wider">
              <div className="col-span-3">Email</div>
              <div className="col-span-2">Name</div>
              <div className="col-span-2">Role</div>
              <div className="col-span-2">Status</div>
              <div className="col-span-1">Joined</div>
              <div className="col-span-2 text-right">Actions</div>
            </div>

            {/* Table Rows */}
            {filteredUsers.map((user) => (
              <div
                key={user.id}
                className="grid grid-cols-1 md:grid-cols-12 gap-4 px-6 py-4 hover:bg-slate-800/20 transition-colors group"
              >
                {/* Email - Always visible */}
                <div className="md:col-span-3">
                  <p className="text-xs text-gray-400 md:hidden font-medium mb-1">Email</p>
                  <div className="flex items-center space-x-2">
                    <Mail className="w-4 h-4 text-gray-500 flex-shrink-0" />
                    <p className="text-sm text-white font-medium break-all">{user.email}</p>
                  </div>
                </div>

                {/* Name */}
                <div className="md:col-span-2">
                  <p className="text-xs text-gray-400 md:hidden font-medium mb-1">Name</p>
                  <p className="text-sm text-gray-300">{user.full_name}</p>
                </div>

                {/* Role */}
                <div className="md:col-span-2">
                  <p className="text-xs text-gray-400 md:hidden font-medium mb-1">Role</p>
                  {changingRole === user.id ? (
                    <div className="inline-flex items-center space-x-1 px-3 py-1">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-400" />
                      <span className="text-xs text-gray-400">Saving...</span>
                    </div>
                  ) : currentUser?.id === user.id ? (
                    <span
                      className={`inline-flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-medium ${getRoleColor(user.role)}`}
                      title="Cannot change your own role"
                    >
                      {getRoleIcon(user.role)}
                      <span className="capitalize">{user.role}</span>
                    </span>
                  ) : (
                    <select
                      value={user.role}
                      onChange={(e) => changeRole(user.id, e.target.value)}
                      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium cursor-pointer border focus:outline-none focus:ring-1 focus:ring-cyan-500/50 transition-colors ${
                        user.role === 'admin'
                          ? 'bg-red-500/20 text-red-400 border-red-500/30'
                          : user.role === 'manager'
                          ? 'bg-orange-500/20 text-orange-400 border-orange-500/30'
                          : user.role === 'engineer'
                          ? 'bg-blue-500/20 text-blue-400 border-blue-500/30'
                          : user.role === 'hr'
                          ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
                          : user.role === 'leader'
                          ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
                          : 'bg-gray-500/20 text-gray-400 border-gray-500/30'
                      }`}
                      style={{ backgroundColor: 'transparent' }}
                    >
                      <option value="admin" className="bg-slate-800 text-red-400">Admin</option>
                      <option value="manager" className="bg-slate-800 text-orange-400">Manager</option>
                      <option value="leader" className="bg-slate-800 text-cyan-400">Leader</option>
                      <option value="engineer" className="bg-slate-800 text-blue-400">Engineer</option>
                      <option value="hr" className="bg-slate-800 text-purple-400">HR</option>
                      <option value="employee" className="bg-slate-800 text-gray-400">Employee</option>
                    </select>
                  )}
                </div>

                {/* Status */}
                <div className="md:col-span-2">
                  <p className="text-xs text-gray-400 md:hidden font-medium mb-1">Status</p>
                  <div className="flex items-center space-x-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        user.is_active ? 'bg-green-500' : 'bg-red-500'
                      }`}
                    />
                    <span className="text-xs text-gray-300">
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                    {!user.is_verified && (
                      <span className="text-xs px-2 py-0.5 bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 rounded">
                        Unverified
                      </span>
                    )}
                  </div>
                </div>

                {/* Joined Date */}
                <div className="md:col-span-1">
                  <p className="text-xs text-gray-400 md:hidden font-medium mb-1">Joined</p>
                  <div className="flex items-center space-x-1">
                    <Calendar className="w-3.5 h-3.5 text-gray-500" />
                    <p className="text-xs text-gray-400">{formatDate(user.created_at)}</p>
                  </div>
                </div>

                {/* Actions */}
                <div className="md:col-span-2 flex justify-end">
                  <button
                    onClick={() => deleteUser(user.id, user.email)}
                    disabled={deleting === user.id}
                    className="p-2 hover:bg-red-500/20 rounded-lg transition-colors text-gray-400 hover:text-red-400 disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Delete user"
                  >
                    {deleting === user.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="mt-4 p-4 bg-slate-800/30 border border-slate-700/50 rounded-lg">
        <p className="text-xs text-gray-400">
          Showing <span className="font-semibold text-white">{filteredUsers.length}</span> of{' '}
          <span className="font-semibold text-white">{users.length}</span> users
        </p>
      </div>
    </div>
  )
}
