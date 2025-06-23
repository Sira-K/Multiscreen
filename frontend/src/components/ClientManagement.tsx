// components/ClientManagement.tsx - Updated with Remove Client Functionality
import React, { useState, useEffect } from 'react';

/**
 * Represents a client device with group support
 */
interface ClientInfo {
  id: string;
  ip: string;
  hostname: string;
  status: 'active' | 'inactive';
  stream_id: string | null;
  group_id: string | null;
  group_name: string | null;
  group_status: string | null;
  srt_port: number;
  display_name?: string | null;
  mac_address?: string;
  platform?: string;
  last_seen: number;
  last_seen_formatted: string;
  time_since_seen?: number;
}

/**
 * Represents a group
 */
interface Group {
  id: string;
  name: string;
  status: string;
  active_clients: number;
  total_clients: number;
  available_streams: string[];
  screen_count: number;
  orientation: string;
  ports?: {
    srt_port: number;
  };
}

/**
 * Props for the ClientManagement component
 */
interface ClientManagementProps {
  clients: ClientInfo[];
  groups: Group[];
  availableStreams: string[];
  assignStreamToClient: (clientId: string, streamId: string) => Promise<any>;
  assignClientToGroup: (clientId: string, groupId: string | null) => Promise<any>;
  renameClient: (clientId: string, newName: string) => Promise<any>;
  removeClient: (clientId: string) => Promise<any>; // Add this new prop
  fetchClients: () => Promise<void>;
  fetchGroups: () => Promise<void>;
  loading: boolean;
  setOutput: (message: string) => void;
  selectedGroupFilter?: string | null;
  onGroupFilterChange?: (groupId: string | null) => void;
}

// For sorting client list
type SortKey = keyof ClientInfo;
type SortDirection = 'asc' | 'desc';

/**
 * Component for managing connected clients with group support and remove functionality
 */
const ClientManagement: React.FC<ClientManagementProps> = ({
  clients,
  groups,
  availableStreams,
  assignStreamToClient,
  assignClientToGroup,
  renameClient,
  removeClient,
  fetchClients,
  fetchGroups,
  loading,
  setOutput,
  selectedGroupFilter,
  onGroupFilterChange
}) => {
  // Client list state
  const [sortedClients, setSortedClients] = useState<ClientInfo[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>('hostname');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  
  // UI state
  const [expandedClientId, setExpandedClientId] = useState<string | null>(null);
  
  // Client editing state
  const [editingClientId, setEditingClientId] = useState<string | null>(null);
  const [isEditingName, setIsEditingName] = useState<string | null>(null);
  const [newDisplayName, setNewDisplayName] = useState<string>("");
  const [selectedStream, setSelectedStream] = useState<string>('');
  const [selectedGroup, setSelectedGroup] = useState<string>('');

// NEW: Remove client state
const [selectedClients, setSelectedClients] = useState<Set<string>>(new Set());
const [showRemoveConfirm, setShowRemoveConfirm] = useState<string | null>(null);
const [showBulkRemoveConfirm, setShowBulkRemoveConfirm] = useState<boolean>(false);
const [showRemoveInactiveConfirm, setShowRemoveInactiveConfirm] = useState<boolean>(false);
const [removeLoading, setRemoveLoading] = useState<boolean>(false);


/**
 * NEW: Remove a single client
 */
const handleRemoveClient = async (clientId: string) => {
  try {
    setRemoveLoading(true);
    await removeClient(clientId); // Use the prop instead of direct API call
    setShowRemoveConfirm(null);
  } catch (error) {
    // Error handling is done in the parent component
  } finally {
    setRemoveLoading(false);
  }
};

/**
 * NEW: Remove multiple selected clients
 */
const removeSelectedClients = async () => {
  if (selectedClients.size === 0) return;

  try {
    setRemoveLoading(true);
    const clientIds = Array.from(selectedClients);
    
    // Remove each client individually using the prop
    for (const clientId of clientIds) {
      await removeClient(clientId);
    }
    
    setSelectedClients(new Set());
    setShowBulkRemoveConfirm(false);
  } catch (error) {
    // Error handling is done in the parent component
  } finally {
    setRemoveLoading(false);
  }
};

/**
 * NEW: Remove all inactive clients
 */
const removeInactiveClients = async () => {
  try {
    setRemoveLoading(true);
    
    // Get inactive clients
    const inactiveClientIds = clients
      .filter(client => client.status === 'inactive')
      .map(client => client.id);
    
    // Remove each inactive client using the prop
    for (const clientId of inactiveClientIds) {
      await removeClient(clientId);
    }
    
    setShowRemoveInactiveConfirm(false);
  } catch (error) {
    // Error handling is done in the parent component
  } finally {
    setRemoveLoading(false);
  }
};


  /**
   * NEW: Toggle client selection
   */
  const toggleClientSelection = (clientId: string) => {
    const newSelected = new Set(selectedClients);
    if (newSelected.has(clientId)) {
      newSelected.delete(clientId);
    } else {
      newSelected.add(clientId);
    }
    setSelectedClients(newSelected);
  };

  /**
   * NEW: Select all visible clients
   */
  const selectAllClients = () => {
    const allClientIds = new Set(filteredClients.map(client => client.id));
    setSelectedClients(allClientIds);
  };

  /**
   * NEW: Clear all selections
   */
  const clearSelection = () => {
    setSelectedClients(new Set());
  };

  /**
   * Get descriptive name for a stream ID - Group-aware
   */
  const getStreamDisplayName = (streamId: string | null, groupId: string | null): string => {
    if (!streamId) return 'None';
    
    // Remove group prefix if present
    const cleanId = streamId.replace(/^live\/[^\/]+\//, '').replace('live/', '');
    
    // Handle the full stream
    if (cleanId === 'test') {
      return 'Full Video';
    }
    
    // Handle numbered streams dynamically
    if (cleanId.startsWith('test')) {
      const streamNumber = parseInt(cleanId.replace('test', ''));
      if (!isNaN(streamNumber)) {
        // Find the group to get available streams count
        const group = groups.find(g => g.id === groupId);
        const totalSplits = group ? group.available_streams.filter(s => s.includes('test') && !s.endsWith('/test')).length : 2;
        
        // Generate descriptive names based on number of splits
        if (totalSplits === 2) {
          return streamNumber === 0 ? 'Left Half' : 'Right Half';
        } else if (totalSplits === 3) {
          const sections = ['Left Third', 'Center Third', 'Right Third'];
          return sections[streamNumber] || `Section ${streamNumber + 1}`;
        } else if (totalSplits === 4) {
          const sections = ['Left Quarter', 'Center-Left', 'Center-Right', 'Right Quarter'];
          return sections[streamNumber] || `Section ${streamNumber + 1}`;
        } else {
          return `Section ${streamNumber + 1} of ${totalSplits}`;
        }
      }
    }
    
    return cleanId;
  };

  /**
   * Get stream options for a specific client based on their group
   */
  const getClientStreamOptions = (client: ClientInfo) => {
    const options = [{ value: '', label: 'None' }];
    
    // If client has a group, use group's available streams
    if (client.group_id) {
      const group = groups.find(g => g.id === client.group_id);
      if (group && group.available_streams) {
        group.available_streams.forEach(stream => {
          options.push({
            value: stream,
            label: getStreamDisplayName(stream, client.group_id)
          });
        });
      }
    } else {
      // Client not in a group, show general streams
      availableStreams.forEach(stream => {
        options.push({
          value: stream,
          label: getStreamDisplayName(stream, null)
        });
      });
    }
    
    return options;
  };

  /**
   * Get group options for client assignment
   */
  const getGroupOptions = () => {
    const options = [{ value: '', label: 'No Group' }];
    
    groups.forEach(group => {
      options.push({
        value: group.id,
        label: `${group.name} (${group.status})`
      });
    });
    
    return options;
  };

  /**
   * Sort clients whenever the client list or sort settings change
   */
  useEffect(() => {
    if (!clients || !Array.isArray(clients)) {
      setSortedClients([]);
      return;
    }

    const sorted = [...clients].sort((a, b) => {
      // Get values for comparison, with fallbacks for display_name
      const valueA = sortKey === 'display_name' 
        ? a.display_name || a.hostname || '' 
        : a[sortKey] || '';
        
      const valueB = sortKey === 'display_name' 
        ? b.display_name || b.hostname || '' 
        : b[sortKey] || '';
      
      // String comparison
      const strA = String(valueA).toLowerCase();
      const strB = String(valueB).toLowerCase();
      
      return sortDirection === 'asc' 
        ? strA.localeCompare(strB) 
        : strB.localeCompare(strA);
    });
    
    setSortedClients(sorted);
  }, [clients, sortKey, sortDirection]);

  /**
   * Handle column header click to change sort
   */
  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
  };

  /**
   * Begin editing a client's stream assignment
   */
  const beginEditingStream = (clientId: string, client: ClientInfo) => {
    setEditingClientId(clientId);
    setSelectedStream(client.stream_id || '');
  };

  /**
   * Begin editing a client's group assignment
   */
  const beginEditingGroup = (clientId: string, client: ClientInfo) => {
    setEditingClientId(clientId);
    setSelectedGroup(client.group_id || '');
  };

  /**
   * Save stream assignment changes
   */
  const saveStreamAssignment = async (clientId: string) => {
    try {
      await assignStreamToClient(clientId, selectedStream);
      setOutput(`Assigned stream to client`);
      setEditingClientId(null);
      await fetchClients();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      setOutput(`Error assigning stream: ${errorMessage}`);
    }
  };

  /**
   * Save group assignment changes
   */
  const saveGroupAssignment = async (clientId: string) => {
    try {
      await assignClientToGroup(clientId, selectedGroup || null);
      setOutput(`Assigned client to group`);
      setEditingClientId(null);
      await fetchClients();
      await fetchGroups(); // Refresh groups to update client counts
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      setOutput(`Error assigning group: ${errorMessage}`);
    }
  };

  /**
   * Begin renaming a client
   */
  const beginRenaming = (clientId: string, currentName: string) => {
    setIsEditingName(clientId);
    setNewDisplayName(currentName || "");
  };

  /**
   * Save client display name changes
   */
  const saveDisplayName = async (clientId: string) => {
    try {
      if (!newDisplayName.trim()) {
        throw new Error("Display name cannot be empty");
      }
      
      await renameClient(clientId, newDisplayName);
      setIsEditingName(null);
      await fetchClients();
      setOutput(`Renamed client to "${newDisplayName}"`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      setOutput(`Error renaming client: ${errorMessage}`);
    }
  };

  /**
   * Toggle expanded details for a client
   */
  const toggleClientDetails = (clientId: string) => {
    setExpandedClientId(expandedClientId === clientId ? null : clientId);
  };

  /**
   * Get display name for a client with fallbacks
   */
  const getDisplayName = (client: ClientInfo) => {
    return client.display_name || client.hostname || 'Unknown Device';
  };

  /**
   * Get SRT command for a client with proper group-specific configuration
   */
  const getSRTCommand = (client: ClientInfo) => {
    const serverIP = import.meta.env.VITE_SRT_IP || 'SERVER_IP';
    const srtPort = client.srt_port || 10080;
    const streamId = client.stream_id || `live/${client.group_id || 'default'}/test`;
    
    return `./cmake-build-debug/player/player 'srt://${serverIP}:${srtPort}?streamid=#!::r=${streamId},m=request,latency=5000000'`;
  };

  /**
   * Render a client's name cell (normal or editing mode)
   */
  const renderNameCell = (client: ClientInfo) => {
    if (isEditingName === client.id) {
      return (
        <div className="name-edit-container">
          <input 
            type="text"
            value={newDisplayName}
            onChange={(e) => setNewDisplayName(e.target.value)}
            className="rename-input"
            placeholder="Enter display name"
          />
          <div className="button-group">
            <button 
              className="save-button small-button" 
              onClick={() => saveDisplayName(client.id)}
              disabled={!newDisplayName.trim()}
            >
              Save
            </button>
            <button 
              className="cancel-button small-button" 
              onClick={() => setIsEditingName(null)}
            >
              Cancel
            </button>
          </div>
        </div>
      );
    }
    
    return (
      <div className="client-name">
        <input
          type="checkbox"
          checked={selectedClients.has(client.id)}
          onChange={() => toggleClientSelection(client.id)}
          className="client-checkbox"
        />
        <span>{getDisplayName(client)}</span>
        <button 
          className="icon-button"
          onClick={() => beginRenaming(client.id, getDisplayName(client))}
          title="Rename this client"
        >
          ✏️
        </button>
      </div>
    );
  };

  /**
   * Render the group assignment cell
   */
  const renderGroupCell = (client: ClientInfo) => {
    if (editingClientId === client.id && selectedGroup !== undefined) {
      const groupOptions = getGroupOptions();
      
      return (
        <div className="group-edit-container">
          <select 
            value={selectedGroup} 
            onChange={(e) => setSelectedGroup(e.target.value)}
            className="group-select"
          >
            {groupOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          
          <div className="button-group">
            <button 
              className="save-button small-button" 
              onClick={() => saveGroupAssignment(client.id)}
            >
              Save
            </button>
            <button 
              className="cancel-button small-button" 
              onClick={() => setEditingClientId(null)}
            >
              Cancel
            </button>
          </div>
        </div>
      );
    }
    
    return (
      <div className="group-display">
        <span className="group-text">
          {client.group_name || 'No Group'}
        </span>
        {client.group_status && (
          <span className={`group-status-badge status-${client.group_status}`}>
            {client.group_status}
          </span>
        )}
        <button
          className="icon-button"
          onClick={() => beginEditingGroup(client.id, client)}
          title="Assign to group"
        >
          👥
        </button>
      </div>
    );
  };

  /**
   * Render the stream assignment cell (normal or editing mode)
   */
  const renderStreamCell = (client: ClientInfo) => {
    if (editingClientId === client.id && selectedStream !== undefined) {
      const streamOptions = getClientStreamOptions(client);
      
      return (
        <div className="stream-edit-container">
          <select 
            value={selectedStream} 
            onChange={(e) => setSelectedStream(e.target.value)}
            className="stream-select"
          >
            {streamOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          
          <div className="button-group">
            <button 
              className="save-button small-button" 
              onClick={() => saveStreamAssignment(client.id)}
            >
              Save
            </button>
            <button 
              className="cancel-button small-button" 
              onClick={() => setEditingClientId(null)}
            >
              Cancel
            </button>
          </div>
        </div>
      );
    }
    
    return (
      <div className="stream-display">
        <span className="stream-text">
          {getStreamDisplayName(client.stream_id, client.group_id)}
        </span>
        <button
          className="icon-button"
          onClick={() => beginEditingStream(client.id, client)}
          disabled={client.status !== 'active'}
          title="Assign stream"
        >
          🔄
        </button>
      </div>
    );
  };

  /**
   * Render connection status
   */
  const renderConnectionStatus = (client: ClientInfo) => {
    const timeSinceSeen = client.time_since_seen || 0;
    const isActive = client.status === 'active';
    
    return (
      <div className="connection-status">
        <span 
          className={`status-badge status-${client.status}`}
          title={`Last seen ${timeSinceSeen.toFixed(1)}s ago`}
        >
          {isActive ? 'Active' : 'Inactive'}
        </span>
      </div>
    );
  };

  /**
   * Render client details when expanded
   */
  const renderClientDetails = (client: ClientInfo) => {
    return (
      <tr className="details-row">
        <td colSpan={8}>
          <div className="client-details">
            <h4>Client Details</h4>
            <div className="details-grid">
              <div className="detail-item">
                <strong>Client ID:</strong> 
                <span className="monospace">{client.id}</span>
              </div>
              <div className="detail-item">
                <strong>MAC Address:</strong> 
                <span className="monospace">{client.mac_address || "Unknown"}</span>
              </div>
              <div className="detail-item">
                <strong>IP Address:</strong> 
                <span className="monospace">{client.ip}</span>
              </div>
              <div className="detail-item">
                <strong>Hostname:</strong> 
                <span>{client.hostname || "Unknown"}</span>
              </div>
              <div className="detail-item">
                <strong>Platform:</strong> 
                <span>{client.platform || "Unknown"}</span>
              </div>
              <div className="detail-item">
                <strong>Status:</strong>
                <span className={`status-badge status-${client.status}`}>
                  {client.status === 'active' ? 'Active' : 'Inactive'}
                </span>
              </div>
              <div className="detail-item">
                <strong>Group:</strong> 
                <span>{client.group_name || "No Group"}</span>
              </div>
              <div className="detail-item">
                <strong>Current Stream:</strong> 
                <span className="monospace">{client.stream_id || "None"}</span>
              </div>
              <div className="detail-item">
                <strong>Stream Description:</strong>
                <span>{getStreamDisplayName(client.stream_id, client.group_id)}</span>
              </div>
              <div className="detail-item">
                <strong>SRT Port:</strong>
                <span className="monospace">{client.srt_port}</span>
              </div>
              <div className="detail-item">
                <strong>Command to run this client:</strong>
                <div className="command-container">
                  <code className="monospace command-text">
                    {getSRTCommand(client)}
                  </code>
                  <button 
                    className="copy-button"
                    onClick={() => {
                      navigator.clipboard.writeText(getSRTCommand(client));
                      setOutput('Command copied to clipboard');
                    }}
                    title="Copy command to clipboard"
                  >
                    📋
                  </button>
                </div>
              </div>
            </div>
          </div>
        </td>
      </tr>
    );
  };

  // Filter clients if group filter is set
  const filteredClients = selectedGroupFilter 
    ? sortedClients.filter(client => client.group_id === selectedGroupFilter)
    : sortedClients;

  // Count inactive clients (for remove inactive button)
  const inactiveClientsCount = filteredClients.filter(client => client.status === 'inactive').length;

  return (
    <div className="client-management">
      <div className="client-header">
        <h2>Connected Clients ({filteredClients.length})</h2>
        <div className="header-controls">
          {/* Group Filter */}
          {onGroupFilterChange && (
            <div className="group-filter">
              <label>Filter by Group:</label>
              <select
                value={selectedGroupFilter || ''}
                onChange={(e) => onGroupFilterChange(e.target.value || null)}
              >
                <option value="">All Groups</option>
                {groups.map(group => (
                  <option key={group.id} value={group.id}>
                    {group.name} ({group.active_clients})
                  </option>
                ))}
              </select>
            </div>
          )}
          
          <button 
            className="refresh-button" 
            onClick={() => 
              {
              fetchClients();
              fetchGroups();
              } 
            }
            disabled={loading}
            title="Manually refresh client list"
          >
            {loading ? 'Refreshing...' : 'Refresh Now'}
          </button>
        </div>
      </div>

      {/* NEW: Bulk Actions Bar */}
      {filteredClients.length > 0 && (
        <div className="bulk-actions-bar">
          <div className="selection-controls">
            <button
              className="select-button"
              onClick={selectAllClients}
              disabled={selectedClients.size === filteredClients.length}
            >
              Select All ({filteredClients.length})
            </button>
            <button
              className="clear-button"
              onClick={clearSelection}
              disabled={selectedClients.size === 0}
            >
              Clear Selection
            </button>
            <span className="selection-count">
              {selectedClients.size} of {filteredClients.length} selected
            </span>
          </div>
          
          <div className="bulk-actions">
            <button
              className="danger-button"
              onClick={() => setShowBulkRemoveConfirm(true)}
              disabled={selectedClients.size === 0 || removeLoading}
            >
              🗑️ Remove Selected ({selectedClients.size})
            </button>
            <button
              className="warning-button"
              onClick={() => setShowRemoveInactiveConfirm(true)}
              disabled={inactiveClientsCount === 0 || removeLoading}
            >
              🧹 Remove Inactive ({inactiveClientsCount})
            </button>
          </div>
        </div>
      )}

      {/* Show group-specific stream info */}
      {selectedGroupFilter && groups.find(g => g.id === selectedGroupFilter) && (
        <div className="group-streams-info">
          <h4>Available Streams for {groups.find(g => g.id === selectedGroupFilter)?.name}:</h4>
          <div className="streams-list">
            {groups.find(g => g.id === selectedGroupFilter)?.available_streams.map(stream => (
              <span key={stream} className="stream-badge">
                {getStreamDisplayName(stream, selectedGroupFilter)}
              </span>
            ))}
          </div>
        </div>
      )}

      {filteredClients.length === 0 ? (
        <div className="no-clients">
          <p>No clients connected. Run the client script on your devices.</p>
          <code>./cmake-build-debug/player/player 'srt://YOUR_SERVER:PORT?streamid=...'</code>
          <p><strong>Note:</strong> Clients must poll every 3 seconds to avoid auto-disconnect</p>
        </div>
      ) : (
        <div className="clients-table-container">
          <table className="clients-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('display_name' as SortKey)}>
                  Name {sortKey === 'display_name' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('ip')}>
                  IP Address {sortKey === 'ip' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('group_name' as SortKey)}>
                  Group {sortKey === 'group_name' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('status')}>
                  Status {sortKey === 'status' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('stream_id')}>
                  Assigned Stream {sortKey === 'stream_id' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('last_seen_formatted' as SortKey)}>
                  Last Seen {sortKey === 'last_seen_formatted' && (sortDirection === 'asc' ? '↑' : '↓')}
                </th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredClients.map((client) => (
                <React.Fragment key={client.id}>
                  <tr className={client.status === 'active' ? 'active-client' : 'inactive-client'}>
                    <td>{renderNameCell(client)}</td>
                    <td>{client.ip}</td>
                    <td>{renderGroupCell(client)}</td>
                    <td>{renderConnectionStatus(client)}</td>
                    <td>{renderStreamCell(client)}</td>
                    <td>{client.last_seen_formatted}</td>
                    <td>
                      <div className="action-buttons">
                        <button
                          className={`details-button ${expandedClientId === client.id ? 'active' : ''}`}
                          onClick={() => toggleClientDetails(client.id)}
                        >
                          {expandedClientId === client.id ? 'Hide' : 'Details'}
                        </button>
                        <button
                          className="danger-button small-button"
                          onClick={() => setShowRemoveConfirm(client.id)}
                          disabled={removeLoading}
                          title="Remove this client"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedClientId === client.id && renderClientDetails(client)}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* NEW: Confirmation Dialogs */}
      
      {/* Single Client Remove Confirmation */}
      {showRemoveConfirm && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Confirm Remove Client</h3>
            <p>
              Are you sure you want to remove client{' '}
              <strong>
                {getDisplayName(clients.find(c => c.id === showRemoveConfirm) || {} as ClientInfo)}
              </strong>?
            </p>
            <p className="warning-text">This action cannot be undone.</p>
            <div className="modal-buttons">
              <button
                onClick={() => setShowRemoveConfirm(null)}
                disabled={removeLoading}
              >
                Cancel
              </button>
              <button
                className="danger-button"
                onClick={() => handleRemoveClient(showRemoveConfirm)}
                disabled={removeLoading}
              >
                {removeLoading ? 'Removing...' : 'Remove Client'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Remove Confirmation */}
      {showBulkRemoveConfirm && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Confirm Bulk Remove</h3>
            <p>
              Are you sure you want to remove <strong>{selectedClients.size}</strong> selected clients?
            </p>
            <div className="client-list">
              {Array.from(selectedClients).slice(0, 5).map(clientId => {
                const client = clients.find(c => c.id === clientId);
                return client ? (
                  <div key={clientId} className="client-item">
                    {getDisplayName(client)}
                  </div>
                ) : null;
              })}
              {selectedClients.size > 5 && (
                <div className="more-clients">
                  ...and {selectedClients.size - 5} more
                </div>
              )}
            </div>
            <p className="warning-text">This action cannot be undone.</p>
            <div className="modal-buttons">
              <button
                onClick={() => setShowBulkRemoveConfirm(false)}
                disabled={removeLoading}
              >
                Cancel
              </button>
              <button
                className="danger-button"
                onClick={removeSelectedClients}
                disabled={removeLoading}
              >
                {removeLoading ? 'Removing...' : `Remove ${selectedClients.size} Clients`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Remove Inactive Confirmation */}
      {showRemoveInactiveConfirm && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Confirm Remove Inactive Clients</h3>
            <p>
              Are you sure you want to remove all <strong>{inactiveClientsCount}</strong> inactive clients?
            </p>
            <p>Clients inactive for more than 5 minutes will be removed.</p>
            <p className="warning-text">This action cannot be undone.</p>
            <div className="modal-buttons">
              <button
                onClick={() => setShowRemoveInactiveConfirm(false)}
                disabled={removeLoading}
              >
                Cancel
              </button>
              <button
                className="danger-button"
                onClick={removeInactiveClients}
                disabled={removeLoading}
              >
                {removeLoading ? 'Removing...' : `Remove ${inactiveClientsCount} Inactive Clients`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ClientManagement;