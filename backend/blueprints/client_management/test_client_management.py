# test_client_management.py
"""
Comprehensive Test Suite for Client Management System
Tests all endpoints, state management, validation, and utilities
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
import sys
import os

# Add the correct backend directory to the path for imports
# Assuming test is in: backend/endpoints/tests/test_client_management.py
# And blueprints is in: backend/endpoints/blueprints/
current_dir = os.path.dirname(__file__)
backend_endpoints_dir = os.path.dirname(current_dir)  # Go up one level to endpoints
sys.path.insert(0, backend_endpoints_dir)

print(f"Current directory: {current_dir}")
print(f"Added to Python path: {backend_endpoints_dir}")
print(f"Looking for blueprints in: {os.path.join(backend_endpoints_dir, 'blueprints')}")

# Import the client management components
try:
    from blueprints.client_management import client_bp
    from blueprints.client_management.client_state import ClientState, client_state
    from blueprints.client_management.client_validators import (
        validate_client_registration,
        validate_group_assignment,
        validate_stream_assignment,
        validate_screen_assignment
    )
    from blueprints.client_management.client_utils import (
        format_time_ago,
        get_next_steps,
        build_stream_url,
        check_screen_availability
    )
    print("✅ Successfully imported client management modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("📁 Available directories:")
    for item in os.listdir(backend_endpoints_dir):
        item_path = os.path.join(backend_endpoints_dir, item)
        if os.path.isdir(item_path):
            print(f"   📂 {item}")
    
    # Try alternative import path
    print("\n🔄 Trying alternative import paths...")
    
    # Check if client_management.py exists as single file
    single_file_path = os.path.join(backend_endpoints_dir, 'blueprints', 'client_management.py')
    if os.path.exists(single_file_path):
        print(f"Found single file: {single_file_path}")
        print("This suggests client_management hasn't been split yet.")
        print("Please run the split first or adjust imports for single file.")
    
    raise

class TestClientState:
    """Test the ClientState class functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.state = ClientState()
        self.state.initialize()
    
    def test_client_state_initialization(self):
        """Test that client state initializes correctly"""
        assert self.state.initialized == True
        assert isinstance(self.state.clients, dict)
        assert len(self.state.clients) == 0
    
    def test_add_and_get_client(self):
        """Test adding and retrieving a client"""
        client_data = {
            "client_id": "test-001",
            "hostname": "test-host",
            "ip_address": "192.168.1.100",
            "display_name": "Test Display",
            "status": "active"
        }
        
        self.state.add_client("test-001", client_data)
        retrieved_client = self.state.get_client("test-001")
        
        assert retrieved_client == client_data
        assert retrieved_client["hostname"] == "test-host"
    
    def test_remove_client(self):
        """Test removing a client"""
        client_data = {"client_id": "test-002", "hostname": "test-host-2"}
        
        self.state.add_client("test-002", client_data)
        assert self.state.get_client("test-002") is not None
        
        removed = self.state.remove_client("test-002")
        assert removed == True
        assert self.state.get_client("test-002") is None
        
        # Try removing non-existent client
        removed_again = self.state.remove_client("test-002")
        assert removed_again == False
    
    def test_get_all_clients(self):
        """Test getting all clients"""
        client1 = {"client_id": "test-001", "hostname": "host1"}
        client2 = {"client_id": "test-002", "hostname": "host2"}
        
        self.state.add_client("test-001", client1)
        self.state.add_client("test-002", client2)
        
        all_clients = self.state.get_all_clients()
        assert len(all_clients) == 2
        assert "test-001" in all_clients
        assert "test-002" in all_clients
    
    def test_get_group_clients(self):
        """Test getting clients by group"""
        client1 = {"client_id": "test-001", "group_id": "group-A"}
        client2 = {"client_id": "test-002", "group_id": "group-A"}
        client3 = {"client_id": "test-003", "group_id": "group-B"}
        
        self.state.add_client("test-001", client1)
        self.state.add_client("test-002", client2)
        self.state.add_client("test-003", client3)
        
        group_a_clients = self.state.get_group_clients("group-A")
        assert len(group_a_clients) == 2
        
        group_b_clients = self.state.get_group_clients("group-B")
        assert len(group_b_clients) == 1
    
    def test_get_active_clients(self):
        """Test getting active clients"""
        current_time = time.time()
        
        # Active client (seen recently)
        active_client = {
            "client_id": "active-001",
            "last_seen": current_time - 30,  # 30 seconds ago
            "group_id": "group-A"
        }
        
        # Inactive client (seen long ago)
        inactive_client = {
            "client_id": "inactive-001",
            "last_seen": current_time - 120,  # 2 minutes ago
            "group_id": "group-A"
        }
        
        self.state.add_client("active-001", active_client)
        self.state.add_client("inactive-001", inactive_client)
        
        active_clients = self.state.get_active_clients()
        assert len(active_clients) == 1
        assert active_clients[0]["client_id"] == "active-001"
        
        # Test with group filter
        group_active = self.state.get_active_clients("group-A")
        assert len(group_active) == 1


class TestClientValidators:
    """Test validation functions"""
    
    def test_validate_client_registration_success(self):
        """Test successful client registration validation"""
        valid_data = {
            "hostname": "test-display-001",
            "display_name": "Test Display 1",
            "platform": "linux",
            "ip_address": "192.168.1.100"
        }
        
        is_valid, error_msg, cleaned_data = validate_client_registration(valid_data)
        
        assert is_valid == True
        assert error_msg is None
        assert cleaned_data["hostname"] == "test-display-001"
        assert cleaned_data["display_name"] == "Test Display 1"
    
    def test_validate_client_registration_missing_hostname(self):
        """Test validation failure for missing hostname"""
        invalid_data = {
            "display_name": "Test Display"
        }
        
        is_valid, error_msg, cleaned_data = validate_client_registration(invalid_data)
        
        assert is_valid == False
        assert "hostname is required" in error_msg
        assert cleaned_data is None
    
    def test_validate_client_registration_invalid_ip(self):
        """Test validation failure for invalid IP"""
        invalid_data = {
            "hostname": "test-host",
            "ip_address": "999.999.999.999"
        }
        
        is_valid, error_msg, cleaned_data = validate_client_registration(invalid_data)
        
        assert is_valid == False
        assert "invalid IP address format" in error_msg
    
    def test_validate_group_assignment(self):
        """Test group assignment validation"""
        valid_data = {
            "client_id": "test-001",
            "group_id": "group-123"
        }
        
        is_valid, error_msg, cleaned_data = validate_group_assignment(valid_data)
        
        assert is_valid == True
        assert cleaned_data["client_id"] == "test-001"
        assert cleaned_data["group_id"] == "group-123"
    
    def test_validate_screen_assignment(self):
        """Test screen assignment validation"""
        valid_data = {
            "client_id": "test-001",
            "group_id": "group-123",
            "screen_number": 2,
            "srt_ip": "192.168.1.100"
        }
        
        is_valid, error_msg, cleaned_data = validate_screen_assignment(valid_data)
        
        assert is_valid == True
        assert cleaned_data["screen_number"] == 2
        assert cleaned_data["srt_ip"] == "192.168.1.100"
    
    def test_validate_screen_assignment_invalid_screen_number(self):
        """Test screen assignment validation with invalid screen number"""
        invalid_data = {
            "client_id": "test-001",
            "group_id": "group-123",
            "screen_number": "invalid"
        }
        
        is_valid, error_msg, cleaned_data = validate_screen_assignment(invalid_data)
        
        assert is_valid == False
        assert "must be a valid integer" in error_msg


class TestClientUtils:
    """Test utility functions"""
    
    def test_format_time_ago(self):
        """Test time formatting function"""
        assert format_time_ago(30) == "30 seconds ago"
        assert format_time_ago(90) == "1 minute ago"
        assert format_time_ago(150) == "2 minutes ago"
        assert format_time_ago(3600) == "1 hour ago"
        assert format_time_ago(7200) == "2 hours ago"
    
    def test_get_next_steps(self):
        """Test next steps generation"""
        # Waiting for assignment
        client_data = {"assignment_status": "waiting_for_assignment"}
        steps = get_next_steps(client_data)
        assert "Wait for admin to assign you to a group" in steps[0]
        
        # Group assigned
        client_data = {"assignment_status": "group_assigned"}
        steps = get_next_steps(client_data)
        assert "specific stream or screen" in steps[0]
        
        # Stream assigned
        client_data = {"assignment_status": "stream_assigned"}
        steps = get_next_steps(client_data)
        assert "Wait for streaming to start" in steps[0]
    
    def test_build_stream_url(self):
        """Test stream URL building"""
        group = {
            "ports": {"srt_port": 10080}
        }
        stream_id = "test123"
        group_name = "test-group"
        srt_ip = "192.168.1.100"
        
        url = build_stream_url(group, stream_id, group_name, srt_ip)
        
        assert "srt://192.168.1.100:10080" in url
        assert "live/test-group/test123" in url
        assert "latency=5000000" in url
    
    def test_check_screen_availability(self):
        """Test screen availability checking"""
        all_clients = {
            "client-001": {
                "client_id": "client-001",
                "group_id": "group-A",
                "screen_number": 0
            },
            "client-002": {
                "client_id": "client-002",
                "group_id": "group-A",
                "screen_number": 1
            }
        }
        
        # Check available screen
        available, conflict = check_screen_availability("client-003", "group-A", 2, all_clients)
        assert available == True
        assert conflict is None
        
        # Check occupied screen
        available, conflict = check_screen_availability("client-003", "group-A", 0, all_clients)
        assert available == False
        assert conflict["client_id"] == "client-001"


class TestClientManagementAPI:
    """Test the Flask API endpoints"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['APP_STATE'] = Mock()
        
        # Register the blueprint
        app.register_blueprint(client_bp, url_prefix='/api/clients')
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @patch('blueprints.client_management.client_endpoints.get_state')
    def test_register_client_success(self, mock_get_state, client):
        """Test successful client registration"""
        # Mock the state
        mock_state = Mock()
        mock_state.get_client.return_value = None  # No existing client
        mock_get_state.return_value = mock_state
        
        registration_data = {
            "hostname": "test-display-001",
            "display_name": "Test Display 1",
            "platform": "linux"
        }
        
        response = client.post('/api/clients/register',
                             data=json.dumps(registration_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] == True
        assert data["client_id"] == "test-display-001"
        assert data["action"] == "registered"
        
        # Verify state was called
        mock_state.add_client.assert_called_once()
    
    def test_register_client_missing_hostname(self, client):
        """Test registration failure with missing hostname"""
        registration_data = {
            "display_name": "Test Display"
        }
        
        response = client.post('/api/clients/register',
                             data=json.dumps(registration_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] == False
        assert "hostname is required" in data["error"]
    
    @patch('blueprints.client_management.info_endpoints.get_state')
    def test_list_clients(self, mock_get_state, client):
        """Test listing clients"""
        # Mock state with clients
        mock_state = Mock()
        current_time = time.time()
        mock_clients = {
            "client-001": {
                "client_id": "client-001",
                "hostname": "display-001",
                "ip_address": "192.168.1.100",
                "display_name": "Display 1",
                "platform": "linux",
                "last_seen": current_time - 30,
                "group_id": "group-A"
            }
        }
        mock_state.get_all_clients.return_value = mock_clients
        mock_get_state.return_value = mock_state
        
        # Mock the docker_management import inside the function
        with patch('docker_management.discover_groups') as mock_discover:
            mock_discover.return_value = {
                "success": True,
                "groups": [
                    {"id": "group-A", "name": "Group A", "docker_running": True}
                ]
            }
            
            response = client.get('/api/clients/list')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] == True
            assert len(data["clients"]) == 1
            assert data["clients"][0]["client_id"] == "client-001"
            assert data["statistics"]["total_clients"] == 1
    
    @patch('blueprints.client_management.admin_endpoints.get_state')
    @patch('blueprints.client_management.admin_endpoints.get_group_from_docker')
    def test_assign_client_to_group(self, mock_get_group, mock_get_state, client):
        """Test assigning client to group"""
        # Mock state
        mock_state = Mock()
        mock_client = {
            "client_id": "client-001",
            "hostname": "display-001",
            "group_id": None
        }
        mock_state.get_client.return_value = mock_client
        mock_get_state.return_value = mock_state
        
        # Mock group
        mock_get_group.return_value = {
            "id": "group-A",
            "name": "Group A",
            "docker_running": True
        }
        
        assignment_data = {
            "client_id": "client-001",
            "group_id": "group-A"
        }
        
        response = client.post('/api/clients/assign_to_group',
                             data=json.dumps(assignment_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] == True
        assert data["new_group_id"] == "group-A"
        
        # Verify state was updated
        mock_state.add_client.assert_called_once()
    
    @patch('blueprints.client_management.client_endpoints.get_state')
    @patch('blueprints.client_management.client_endpoints.get_group_from_docker')
    @patch('blueprints.client_management.client_endpoints.check_group_streaming_status')
    def test_wait_for_assignment_ready(self, mock_streaming, mock_get_group, mock_get_state, client):
        """Test wait for assignment when stream is ready"""
        # Mock state
        mock_state = Mock()
        mock_client = {
            "client_id": "client-001",
            "hostname": "display-001",
            "group_id": "group-A",
            "assignment_status": "stream_assigned",
            "stream_url": "srt://192.168.1.100:10080?streamid=test"
        }
        mock_state.get_client.return_value = mock_client
        mock_get_state.return_value = mock_state
        
        # Mock group and streaming
        mock_get_group.return_value = {
            "id": "group-A",
            "name": "Group A",
            "docker_running": True
        }
        mock_streaming.return_value = True
        
        wait_data = {"client_id": "client-001"}
        
        response = client.post('/api/clients/wait_for_assignment',
                             data=json.dumps(wait_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ready_to_play"
        assert "stream_url" in data
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        with patch('blueprints.client_management.info_endpoints.get_state') as mock_get_state:
            mock_state = Mock()
            mock_state.initialized = True
            mock_state.get_all_clients.return_value = {}
            mock_get_state.return_value = mock_state
            
            response = client.get('/api/clients/health')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] == True
            assert data["status"] == "healthy"


class TestIntegration:
    """Integration tests for the complete workflow"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app for integration tests"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.config['APP_STATE'] = Mock()
        app.register_blueprint(client_bp, url_prefix='/api/clients')
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_complete_client_workflow(self, client):
        """Test complete workflow: register -> assign -> wait -> ready"""
        with patch.multiple(
            'blueprints.client_management.client_endpoints',
            get_state=Mock(),
            get_group_from_docker=Mock(),
            check_group_streaming_status=Mock()
        ), patch.multiple(
            'blueprints.client_management.admin_endpoints',
            get_state=Mock(),
            get_group_from_docker=Mock(),
            get_persistent_streams_for_group=Mock()
        ):
            
            # Step 1: Register client
            registration_data = {
                "hostname": "integration-test-001",
                "display_name": "Integration Test Display"
            }
            
            register_response = client.post('/api/clients/register',
                                          data=json.dumps(registration_data),
                                          content_type='application/json')
            
            assert register_response.status_code == 200
            
            # Step 2: Test assignment workflow would continue here
            # (This is a simplified integration test due to mocking complexity)


def run_tests():
    """Run all tests with pytest"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    # Run tests if this file is executed directly
    print("🧪 Running Client Management Tests...")
    print("=" * 60)
    
    # You can run specific test classes
    print("\n📊 Testing Client State Management...")
    pytest.main([__file__ + "::TestClientState", "-v"])
    
    print("\n🔍 Testing Validators...")
    pytest.main([__file__ + "::TestClientValidators", "-v"])
    
    print("\n🛠️  Testing Utilities...")
    pytest.main([__file__ + "::TestClientUtils", "-v"])
    
    print("\n🌐 Testing API Endpoints...")
    pytest.main([__file__ + "::TestClientManagementAPI", "-v"])
    
    print("\n🔗 Testing Integration...")
    pytest.main([__file__ + "::TestIntegration", "-v"])
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")