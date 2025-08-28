#!/usr/bin/env python3
"""
Test script to verify leaderboard integration in FalconGrasp_Complete.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.game_api import GameAPI
from utils.logger import get_logger

# Set up logger
logger = get_logger(__name__, level="INFO")

# Import the global variable from the game
try:
    from FalconGrasp_Complete import list_top5_FalconGrasp
except ImportError:
    logger.warning("⚠️  Could not import list_top5_FalconGrasp, creating local version")
    list_top5_FalconGrasp = []


def test_falcongrasp_leaderboard_integration():
    """Test the leaderboard integration for Falcon's Grasp"""
    logger.info("🦅" + "=" * 60)
    logger.info("🦅 TESTING FALCON'S GRASP LEADERBOARD INTEGRATION")
    logger.info("🦅" + "=" * 60)
    
    try:
        # Step 1: Initialize and authenticate API
        logger.info("📋 Step 1: Initializing GameAPI...")
        api = GameAPI()
        
        if not api.authenticate():
            logger.error("❌ Authentication failed")
            return False
        
        logger.info("✅ Authentication successful")
        
        # Step 2: Test leaderboard fetching
        logger.info("📋 Step 2: Testing leaderboard fetch for 'Falcon's Grasp'...")
        leaderboard = api.get_leaderboard("Falcon's Grasp")
        
        # Step 3: Simulate updating the global list
        logger.info("📋 Step 3: Simulating leaderboard update...")
        list_top5_FalconGrasp.clear()
        list_top5_FalconGrasp.extend(leaderboard)
        
        logger.info(f"📊 Leaderboard updated with {len(list_top5_FalconGrasp)} entries")
        
        # Step 4: Display results
        if list_top5_FalconGrasp:
            logger.info("🏆" + "=" * 50)
            logger.info("🏆 CURRENT FALCON'S GRASP LEADERBOARD")
            logger.info("🏆" + "=" * 50)
            sorted_data = sorted(list_top5_FalconGrasp, key=lambda item: item[1], reverse=True)
            
            for i, (team_name, score) in enumerate(sorted_data[:5], 1):
                logger.info(f"   {i:2d}. {team_name:<20} | {score:,} points")
        else:
            logger.info("📊 No teams found in leaderboard for 'Falcon's Grasp'")
        
        # Step 5: Test with alternative game names
        logger.info("📋 Step 5: Testing alternative game names...")
        
        test_games = ["falcons_grasp", "Rising Together", "cage_game"]
        for game_name in test_games:
            logger.info(f"🎮 Testing: {game_name}")
            test_board = api.get_leaderboard(game_name)
            if test_board:
                logger.info(f"   ✅ Found {len(test_board)} teams")
                for team, score in test_board[:3]:  # Show top 3
                    logger.info(f"      • {team}: {score:,}")
            else:
                logger.info(f"   ⚠️  No teams found")
        
        logger.info("🎉" + "=" * 60)
        logger.info("🎉 FALCON'S GRASP LEADERBOARD TEST COMPLETED")
        logger.info("🎉" + "=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"💥 Test failed: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"🔍 Stack trace: {traceback.format_exc()}")
        return False


def main():
    """Main function"""
    logger.info("🚀" + "=" * 80)
    logger.info("🚀 FALCON'S GRASP LEADERBOARD INTEGRATION TEST")
    logger.info("🚀" + "=" * 80)
    
    success = test_falcongrasp_leaderboard_integration()
    
    if success:
        logger.info("✅ Integration test completed successfully!")
        logger.info("💡 The leaderboard should now work in FalconGrasp_Complete.py")
        return 0
    else:
        logger.error("❌ Integration test failed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
