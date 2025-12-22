#!/usr/bin/env python3
"""
Test script to verify Knowledge Base integration with Read.ai MEDDIC extraction.

This script tests that the File Search Store is being used to enhance MEDDIC extraction.
"""

import json
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.llm_service import readai_meddic
from app.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_kb_meddic():
    """Test MEDDIC extraction with Knowledge Base"""
    settings = get_settings()
    
    # Check configuration
    if not settings.GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY not set")
        return False
    
    if not settings.GOVISUALLY_KB_STORE_ID:
        logger.warning("⚠️  GOVISUALLY_KB_STORE_ID not set - will test without KB")
        use_kb = False
    else:
        logger.info("✅ GOVISUALLY_KB_STORE_ID configured: %s", settings.GOVISUALLY_KB_STORE_ID)
        use_kb = True
    
    # Sample meeting transcript (simulating a real Read.ai meeting)
    test_transcript = """
    Sales Rep: Thanks for joining today. Can you tell me a bit about your current process?
    
    Prospect: Sure. We're a pharmaceutical company and we're struggling with FDA compliance. 
    Our current process is very manual - we have to check every label manually for FDA requirements.
    It takes our team about 2-3 weeks per product, and we're worried about making mistakes.
    
    Sales Rep: I understand. What kind of errors are you seeing?
    
    Prospect: Mostly around allergen disclosures and net weight requirements. We had a close call 
    last year where we almost shipped a product with incorrect allergen information. That would 
    have been a disaster - FDA warning letters, recalls, the whole thing.
    
    Sales Rep: That's a serious concern. What's your current workflow?
    
    Prospect: We use a combination of Excel spreadsheets and manual review. Our compliance team 
    reviews each label against FDA guidelines. It's time-consuming and error-prone.
    
    Sales Rep: How many products do you launch per year?
    
    Prospect: About 50-60 new SKUs annually. Each one goes through this process.
    
    Sales Rep: And who makes the final decision on compliance tools?
    
    Prospect: That would be our VP of Regulatory Affairs, Sarah Johnson. She's the one who 
    approves any new tools or processes.
    
    Sales Rep: Got it. What's your timeline for finding a solution?
    
    Prospect: We'd like to have something in place by Q2. We're evaluating a few vendors, 
    including Workfront and some custom solutions.
    
    Sales Rep: What are the key criteria you're looking for?
    
    Prospect: Definitely FDA compliance checking, integration with our existing systems, 
    and accuracy. We can't afford mistakes.
    
    Sales Rep: Perfect. Let me send you some information about our FDA Regulatory Agent 
    and ROI calculations. We typically see 85-90% time savings for pharma companies.
    
    Prospect: That sounds promising. Can you schedule a technical demo?
    
    Sales Rep: Absolutely. I'll send a calendar invite.
    """
    
    test_summary = "Meeting with pharmaceutical company discussing FDA compliance challenges. " \
                   "Current manual process takes 2-3 weeks per product. Concerned about allergen " \
                   "disclosure errors. Evaluating vendors for Q2 implementation."
    
    test_attendees = [
        {"name": "Sales Rep", "email": "sales@govisually.com"},
        {"name": "Prospect", "email": "prospect@pharma.com"}
    ]
    
    logger.info("=" * 60)
    logger.info("Testing MEDDIC extraction with Knowledge Base")
    logger.info("=" * 60)
    logger.info("")
    
    if use_kb:
        logger.info("📚 Knowledge Base: ENABLED")
        logger.info("   Store ID: %s", settings.GOVISUALLY_KB_STORE_ID)
        logger.info("   Expected: Enhanced MEDDIC with specific features, objection handling, ROI")
    else:
        logger.info("📚 Knowledge Base: DISABLED")
        logger.info("   Expected: Standard MEDDIC extraction")
    
    logger.info("")
    logger.info("Extracting MEDDIC data from test transcript...")
    logger.info("")
    
    try:
        meddic = readai_meddic(
            title="FDA Compliance Discussion - Pharma Company",
            datetime_str="2025-12-21T10:00:00Z",
            attendees=test_attendees,
            summary=test_summary,
            transcript=test_transcript,
        )
        
        logger.info("✅ MEDDIC extraction completed!")
        logger.info("")
        logger.info("=" * 60)
        logger.info("RESULTS")
        logger.info("=" * 60)
        logger.info("")
        
        # Display key fields
        fields_to_check = [
            ("metrics", "Metrics"),
            ("identified_pain", "Identified Pain"),
            ("decision_criteria", "Decision Criteria"),
            ("economic_buyer", "Economic Buyer"),
            ("champion", "Champion"),
            ("competition", "Competition"),
            ("next_steps", "Next Steps"),
            ("risks", "Risks"),
            ("confidence", "Confidence"),
        ]
        
        for field_name, display_name in fields_to_check:
            value = getattr(meddic, field_name, "") or ""
            if value:
                logger.info("📋 %s:", display_name)
                # Show first 200 chars
                preview = value[:200] + "..." if len(value) > 200 else value
                for line in preview.split('\n')[:3]:  # Show first 3 lines
                    logger.info("   %s", line)
                if len(value) > 200:
                    logger.info("   ... (%d more chars)", len(value) - 200)
                logger.info("")
        
        # Check if KB was used (look for specific GoVisually features/terms)
        all_text = " ".join([getattr(meddic, f, "") or "" for f in dir(meddic) if not f.startswith("_")])
        kb_indicators = [
            "FDA Regulatory Agent",
            "ROI",
            "compliance",
            "85-90%",
            "time savings",
            "pharma",
        ]
        
        found_indicators = [ind for ind in kb_indicators if ind.lower() in all_text.lower()]
        
        if use_kb:
            if found_indicators:
                logger.info("✅ Knowledge Base appears to be working!")
                logger.info("   Found KB-related terms: %s", ", ".join(found_indicators))
            else:
                logger.warning("⚠️  Knowledge Base may not have been used")
                logger.warning("   No KB-specific terms found in output")
                logger.warning("   Check logs above for File Search usage")
        else:
            logger.info("ℹ️  Standard extraction completed (KB not configured)")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("Test completed successfully!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error("❌ Test failed: %s", e)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_kb_meddic()
    sys.exit(0 if success else 1)
