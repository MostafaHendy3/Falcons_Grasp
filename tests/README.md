# Test Suite for Falcon's Grasp Game

This directory contains test files for the Falcon's Grasp (FalconGrasp) game application.

## Test Files

### Leaderboard Integration Tests
- **`test_falcongrasp_leaderboard.py`** - Integration test for Falcon's Grasp leaderboard
  - Tests leaderboard integration with the main game application
  - Verifies API connectivity for "Falcon's Grasp" game name
  - Simulates the global list_top5_FalconGrasp updates
  - Run with: `python test_falcongrasp_leaderboard.py`

## Running Tests

### Individual Tests
```bash
cd tests
python test_falcongrasp_leaderboard.py    # Run leaderboard integration test
```

### All Python Tests (when more tests are added)
```bash
cd tests
python -m unittest discover -s . -p "test_*.py" -v
```

## Test Requirements

- Python 3.7+
- Required packages: requests, PyQt5
- Active internet connection for API tests
- Valid API credentials in config.py

## Notes

- Tests use the real GameAPI to verify integration
- API tests require valid authentication credentials
- Log files are created in the parent `logs/` directory when testing
- The test verifies "Falcon's Grasp" leaderboard specifically

## Test Coverage

- ✅ GameAPI initialization and authentication
- ✅ Leaderboard fetching for "Falcon's Grasp"
- ✅ Global variable updates (list_top5_FalconGrasp)
- ✅ Alternative game name testing
- ✅ Error handling and logging
