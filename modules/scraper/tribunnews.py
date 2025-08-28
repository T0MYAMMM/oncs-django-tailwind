#!/usr/bin/env python3
"""
Test script for custom Tribunnews scraper
"""

import json
from scrapers.zyte.check_portal_scraper import get_tribunnews_content

def test_tribunnews_scraper(url):
    """Test the custom Tribunnews scraper with a specific URL."""
    
    # Test URL
    #url = "https://www.tribunnews.com/regional/2025/06/12/anggota-tni-terluka-dalam-bentrok-antar-pemuda-di-ambon-polisi-dipicu-dendam"
    
    print("🔍 Testing Custom Tribunnews Scraper")
    print("=" * 60)
    print(f"URL: {url}")
    print("=" * 60)
    
    try:
        # Get content using custom scraper
        content = get_tribunnews_content(url)
        
        if content:
            print("✅ SUCCESS! Content extracted successfully\n")
            
            # Display extracted content
            print("📰 EXTRACTED CONTENT:")
            print("-" * 40)
            
            print(f"🏷️  Title: {content.get('title', 'N/A')}")
            print(f"🌐 Source: {content.get('source_name', 'N/A')}")
            print(f"📅 Date Published: {content.get('date_published', 'N/A')}")
            print(f"👥 Authors: {', '.join(content.get('author_list', [])) if content.get('author_list') else 'N/A'}")
            print(f"🌍 Language: {content.get('language', 'N/A')}")
            print(f"🔗 Link: {content.get('link', 'N/A')}")
            
            description = content.get('description', '')
            if description:
                print(f"📝 Description: {description[:200]}{'...' if len(description) > 200 else ''}")
            else:
                print("📝 Description: N/A")
            
            body = content.get('body', '')
            if body:
                print(f"📄 Body: {body[:300]}{'...' if len(body) > 300 else ''}")
                print(f"📊 Body Length: {len(body)} characters")
            else:
                print("📄 Body: N/A")
            
            images = content.get('images', [])
            if images:
                print(f"🖼️  Images: {len(images)} found")
                for i, img in enumerate(images[:3], 1):  # Show first 3 images
                    print(f"   {i}. {img}")
                if len(images) > 3:
                    print(f"   ... and {len(images) - 3} more")
            else:
                print("🖼️  Images: None found")
            
            print("\n" + "=" * 60)
            print("✅ Test completed successfully!")
            
            # Validate required fields
            print("\n🔍 VALIDATION:")
            print("-" * 20)
            
            if content.get('title'):
                print("✅ Title: Present")
            else:
                print("❌ Title: Missing")
            
            if content.get('body') and len(content.get('body', '')) > 0:
                print("✅ Body: Present")
            else:
                print("❌ Body: Missing or empty")
            
            if content.get('date_published'):
                print("✅ Date: Present")
            else:
                print("❌ Date: Missing")
            
            if content.get('source_name'):
                print("✅ Source: Present")
            else:
                print("❌ Source: Missing")
            
        else:
            print("❌ FAILED! No content extracted")
            print("This could be due to:")
            print("- Network connectivity issues")
            print("- HTML API server unavailable")
            print("- Page structure changes")
            print("- Invalid URL")
            
    except Exception as e:
        print(f"❌ ERROR! Exception occurred: {e}")
        import traceback
        traceback.print_exc()

def test_with_json_output():
    """Test and show JSON output for debugging."""
    url = "https://kaltim.tribunnews.com/2025/07/25/5-negara-pertama-berhasil-tekan-tarif-impor-donald-trump-salah-satunya-indonesia"
    
    print("\n" + "=" * 60)
    print("🔧 JSON OUTPUT (for debugging):")
    print("=" * 60)
    
    try:
        content = get_tribunnews_content(url)
        if content:
            print(json.dumps(content, indent=2, ensure_ascii=False))
        else:
            print("No content returned")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    url = "https://kaltim.tribunnews.com/2025/07/25/5-negara-pertama-berhasil-tekan-tarif-impor-donald-trump-salah-satunya-indonesia"
    test_tribunnews_scraper(url)
    
    # Uncomment the line below to see JSON output
    # test_with_json_output() 