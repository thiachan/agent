"""
Re-ingest demo video documents with enriched descriptions and proper metadata.

This script:
1. Deletes existing demo video chunks from ChromaDB
2. Re-ingests each demo video doc with:
   - Real product descriptions (not boilerplate)
   - Tags stored in metadata (not just content)
   - Category and content_type in metadata
   - Single-chunk storage (small docs stay intact)

Usage:
    cd /home/ubuntu/AGENT
    source backend/venv/bin/activate
    python -m scripts.reingest_demo_videos
"""

import sys
import os
import logging
import re

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# ─── Enriched video document data ────────────────────────────────────────────
# Each entry: (doc_id, filename, youtube_url, category, tags, product_name, description)

ENRICHED_VIDEOS = [
    {
        "doc_id": 8,
        "filename": "AI_model_protection_AI_vulnerability_detection_demo-video.docx",
        "url": "https://www.youtube.com/watch?v=I11eIbxFLjE",
        "category": "AI Model Protection",
        "tags": "AI Model Protection, AI Security, Model Protection, AI Vulnerability Detection, Vulnerability Scanning, AI Defense, Demo Video",
        "product": "AI Model Protection - AI Vulnerability Detection",
        "description": (
            "AI Vulnerability Detection identifies security weaknesses in deployed AI and machine learning models. "
            "It scans AI models for known vulnerability patterns including adversarial attack surfaces, data poisoning risks, "
            "model inversion threats, and prompt injection vulnerabilities. The tool provides automated vulnerability assessments "
            "with severity ratings, remediation guidance, and continuous monitoring to ensure AI systems remain secure against "
            "emerging threats. It integrates with CI/CD pipelines for pre-deployment security validation."
        ),
    },
    {
        "doc_id": 9,
        "filename": "AI_model_protection_AI-app_AI-applications_demo_video.docx",
        "url": "https://www.youtube.com/watch?v=Qiz2wIjbz5g",
        "category": "AI Model Protection",
        "tags": "AI Model Protection, AI Security, Model Protection, AI Applications, AI App Security, Application Protection, Demo Video",
        "product": "AI Model Protection - AI Application Security",
        "description": (
            "AI Application Security protects AI-powered applications from runtime attacks and misuse. "
            "It monitors AI application behavior in real-time, detecting anomalous inference requests, prompt injection attempts, "
            "data exfiltration through model outputs, and unauthorized API access patterns. The solution provides guardrails "
            "for LLM-based applications, validates input/output boundaries, and enforces content safety policies. "
            "It supports multi-model architectures and provides centralized visibility across all AI application deployments."
        ),
    },
    {
        "doc_id": 10,
        "filename": "AI_model_protection_asset_discovery_detection_demo_video.docx",
        "url": "https://www.youtube.com/watch?v=lCNDRtn4x1c",
        "category": "AI Model Protection",
        "tags": "AI Model Protection, AI Security, Model Protection, Asset Discovery, AI Asset Detection, Shadow AI, Demo Video",
        "product": "AI Model Protection - Asset Discovery & Detection",
        "description": (
            "AI Asset Discovery & Detection automatically identifies and catalogs all AI and machine learning assets "
            "across the organization, including shadow AI deployments. It discovers AI models, training pipelines, "
            "data stores, inference endpoints, and API integrations that may be running without security oversight. "
            "The tool provides a comprehensive AI asset inventory with risk scoring, classifies models by sensitivity level, "
            "and alerts security teams to unregistered or non-compliant AI deployments."
        ),
    },
    {
        "doc_id": 11,
        "filename": "Cloud Edge_Automated Cloud Security Orchestration_MCD_demo-video.docx",
        "url": "https://www.youtube.com/watch?v=xQyMoXB2dIg",
        "category": "Cloud Edge",
        "tags": "Cloud Edge, Cloud Security, Edge Security, MCD, Multicloud Defense, Automated Cloud Security Orchestration, Demo Video",
        "product": "Automated Cloud Security Orchestration (MCD / Multicloud Defense)",
        "description": (
            "Multicloud Defense (MCD) provides automated cloud security orchestration across AWS, Azure, GCP, and OCI. "
            "It delivers unified firewall policy management, automated threat response, and consistent security posture "
            "across all cloud environments. MCD automates security workflows including policy deployment, compliance checks, "
            "and incident remediation. It provides centralized visibility into cloud workloads, east-west traffic inspection, "
            "and ingress/egress filtering with dynamic policy adaptation based on cloud-native context signals."
        ),
    },
    {
        "doc_id": 12,
        "filename": "Cloud_Edge_Dynamic Tag-based Policy_demo-video.docx",
        "url": "https://www.youtube.com/watch?v=nMVqe_SWFsk",
        "category": "Cloud Edge",
        "tags": "Cloud Edge, Cloud Security, Edge Security, SGT, Security Group Tags, Tag-based Policy, Dynamic Policy, Demo Video",
        "product": "Cloud Edge Dynamic Tag-based Policy",
        "description": (
            "Dynamic Tag-based Policy enables intent-based security using Security Group Tags (SGTs) in cloud edge environments. "
            "It allows security teams to define policies based on logical tags rather than IP addresses, enabling dynamic "
            "microsegmentation that follows workloads as they move across cloud and on-premises environments. "
            "Policies automatically adapt when workloads scale, migrate, or change state. The solution integrates with "
            "Cisco ISE for identity-based tagging and supports both cloud-native tags and SGT-based classification."
        ),
    },
    {
        "doc_id": 13,
        "filename": "DC_Edge_AIOps_SCC_demo-video.docx",
        "url": "https://www.youtube.com/watch?v=SaO5ZbjVt6Q",
        "category": "DC Edge",
        "tags": "DC Edge, Data Center Edge, Edge Security, AIOps, Security Cloud Control, SCC, AI Operations, Demo Video",
        "product": "AIOps with Security Cloud Control (SCC)",
        "description": (
            "AIOps with Security Cloud Control (SCC) brings AI-driven operational intelligence to Cisco security infrastructure. "
            "It uses machine learning to analyze firewall logs, policy configurations, and traffic patterns to identify "
            "misconfigurations, policy conflicts, and optimization opportunities. SCC provides proactive health monitoring, "
            "automated change management, and predictive analytics for capacity planning. "
            "Key features include policy hit-count analysis, rule optimization recommendations, device health scoring, "
            "and AI-assisted troubleshooting for Secure Firewall deployments."
        ),
    },
    {
        "doc_id": 14,
        "filename": "DC_Edge_Eve_Encrypted_Visibility_Engine_demo-video.docx",
        "url": "https://www.youtube.com/watch?v=ORccD2_glBw",
        "category": "DC Edge",
        "tags": "DC Edge, Data Center Edge, Edge Security, EVE, Encrypted Visibility Engine, Encrypted Traffic Analytics, TLS, Demo Video",
        "product": "Encrypted Visibility Engine (EVE)",
        "description": (
            "The Encrypted Visibility Engine (EVE) detects malware and threats hidden in encrypted traffic without decryption. "
            "EVE uses machine learning to analyze TLS/SSL connection metadata — including JA3/JA3S fingerprints, "
            "certificate details, flow timing, and packet size distributions — to identify malicious activity within "
            "encrypted sessions. It works with TLS 1.3 and supports detection of command-and-control traffic, "
            "data exfiltration, and known malware families. EVE integrates natively with Cisco Secure Firewall "
            "and provides encrypted traffic visibility without the performance or privacy impact of full decryption."
        ),
    },
    {
        "doc_id": 15,
        "filename": "DC_Edge_SnortML_Zero_Day_Machine_Learning_demo-video.docx",
        "url": "https://www.youtube.com/watch?v=t2pwY_UiiwQ",
        "category": "DC Edge",
        "tags": "DC Edge, Data Center Edge, Edge Security, SnortML, Snort ML, Zero Day, Zero Day Threat Defense, Machine Learning, IPS, IDS, Demo Video",
        "product": "SnortML (Zero Day Machine Learning)",
        "description": (
            "SnortML brings machine learning-powered zero-day threat detection to the Snort intrusion prevention system. "
            "Unlike traditional signature-based IPS that can only detect known threats, SnortML uses trained ML models "
            "to identify previously unseen exploits and attack techniques in network traffic. It analyzes packet payloads "
            "and flow behaviors to detect novel buffer overflows, shellcode variants, and protocol anomalies. "
            "SnortML operates inline with minimal latency impact, integrates with Cisco Secure Firewall, "
            "and continuously updates its models through Cisco Talos threat intelligence."
        ),
    },
    {
        "doc_id": 16,
        "filename": "macro_micro_seg_global_visualization_demo-video.docx",
        "url": "https://www.youtube.com/watch?v=qHPisq6yhsA",
        "category": "Macro Micro Segmentation",
        "tags": "Macro Segmentation, Micro Segmentation, Segmentation, Network Segmentation, Global Visualization, Traffic Visualization, Security Visibility, Demo Video",
        "product": "Macro/Micro Segmentation – Global Visualization",
        "description": (
            "Global Visualization provides a comprehensive, real-time view of network segmentation across the entire organization. "
            "It maps all communication flows between macro segments (VLANs, VRFs, zones) and micro segments (workload-level), "
            "showing allowed and denied traffic patterns in an interactive topology. Security teams can identify "
            "policy gaps, lateral movement risks, and compliance violations through visual drill-downs. "
            "The dashboards aggregate data from firewalls, switches, and endpoint agents to provide end-to-end "
            "segmentation visibility across campus, data center, and branch environments."
        ),
    },
    {
        "doc_id": 17,
        "filename": "macro_micro_seg_policy-discovery-analysis_demo-video copy.docx",
        "url": "https://www.youtube.com/watch?v=jbWornsuOSg",
        "category": "Macro Micro Segmentation",
        "tags": "Macro Segmentation, Micro Segmentation, Segmentation, Network Segmentation, Policy Discovery, Policy Analysis, Traffic Analysis, Demo Video",
        "product": "Macro/Micro Segmentation – Policy Discovery & Analysis",
        "description": (
            "Policy Discovery & Analysis automates the process of understanding existing network communication patterns "
            "to build accurate segmentation policies. It passively monitors traffic flows across the network to discover "
            "which workloads and applications communicate with each other, then recommends optimal segmentation policies. "
            "The tool analyzes protocol usage, port ranges, traffic volumes, and application dependencies to create "
            "least-privilege policies. It provides what-if analysis to simulate policy impact before enforcement, "
            "reducing the risk of breaking legitimate communications during segmentation rollout."
        ),
    },
    {
        "doc_id": 18,
        "filename": "macro_micro_seg_unified_policy_mgmt_demo-video.docx",
        "url": "https://www.youtube.com/watch?v=tM4RiZ8d--s",
        "category": "Macro Micro Segmentation",
        "tags": "Macro Segmentation, Micro Segmentation, Segmentation, Network Segmentation, Unified Policy Management, Policy Management, Centralized Management, Demo Video",
        "product": "Macro/Micro Segmentation – Unified Policy Management",
        "description": (
            "Unified Policy Management provides a single pane of glass to create, manage, and enforce segmentation policies "
            "across all network domains — campus, data center, branch, and cloud. It enables consistent policy definition "
            "using business-intent language, automatically translating high-level segmentation goals into device-specific "
            "configurations across heterogeneous infrastructure (Secure Firewall, switches, ACI, cloud gateways). "
            "The platform tracks policy versions, provides audit trails, and ensures compliance with regulatory requirements "
            "by maintaining a centralized policy repository with role-based access controls."
        ),
    },
    {
        "doc_id": 19,
        "filename": "smart_switch_hypershield_L4-Segmentation_demo-video.docx",
        "url": "https://www.youtube.com/watch?v=4d13wgB9k3c",
        "category": "Smart Switch",
        "tags": "Smart Switch, L4 Switch, Switch, Hypershield, L4 Segmentation, Layer 4, Layer 4 Segmentation, Cisco Hypershield, Demo Video",
        "product": "Hypershield L4 Segmentation (Smart Switch)",
        "description": (
            "Cisco Hypershield with L4 (Layer 4) Segmentation enforces security policies directly at the network switch level, "
            "providing hardware-accelerated microsegmentation without deploying agents on endpoints. "
            "Smart switches apply Layer 4 access control based on IP addresses, ports, and protocols at line rate, "
            "enabling east-west traffic control within the data center and campus. Hypershield leverages distributed "
            "enforcement points embedded in the switching infrastructure, automatically segmenting workloads based on "
            "identity and context. This approach delivers firewall-grade segmentation at switch speed with zero "
            "performance overhead and simplified management through centralized policy orchestration."
        ),
    },
    {
        "doc_id": 20,
        "filename": "Zone_Seg_branch_context-aware_demo-video.docx",
        "url": "https://www.youtube.com/watch?v=WIzk34M7Y2M",
        "category": "Zone Segmentation",
        "tags": "Zone Segmentation, Segmentation, Network Segmentation, Branch, Branch Security, Context-Aware, SD-WAN, Demo Video",
        "product": "Zone Segmentation – Branch Context-Aware Security",
        "description": (
            "Branch Context-Aware Security extends zone-based segmentation to branch office networks using contextual signals. "
            "It segments branch traffic based on user identity, device type, application, and location rather than just "
            "network topology. Integrated with SD-WAN and Cisco ISE, it enforces differentiated policies for guest, "
            "IoT, employee, and server traffic at the branch. The solution dynamically adjusts segmentation as devices "
            "connect or roam, providing consistent security without manual VLAN management at each branch. "
            "It supports zero-trust principles by validating context before granting access to segmented resources."
        ),
    },
    {
        "doc_id": 21,
        "filename": "Zone_Seg_Campus_Context_Aware_SGT_Tags_demo-video.docx",
        "url": "https://www.youtube.com/watch?v=sCSXQq5GIhI",
        "category": "Zone Segmentation",
        "tags": "Zone Segmentation, Segmentation, Network Segmentation, Campus, SGT, Security Group Tags, Tag-based Policy, Context-Aware, ISE, TrustSec, Demo Video",
        "product": "Zone Segmentation – Campus Context-Aware SGT Tags",
        "description": (
            "Campus Context-Aware SGT (Security Group Tag) segmentation uses Cisco TrustSec and ISE to apply identity-based "
            "segmentation across the campus network. Users and devices are dynamically classified into security groups based "
            "on authentication, posture assessment, and contextual attributes (role, device type, location, time). "
            "SGTs travel with traffic across the switching infrastructure, enabling policy enforcement at every hop "
            "without complex ACL management. The SGACL (Security Group ACL) matrix defines which groups can communicate, "
            "providing scalable microsegmentation that adapts as users move between buildings, floors, and wireless APs."
        ),
    },
    {
        "doc_id": 22,
        "filename": "Zone_Seg_Campus_RTC_FTD_ISE_demo-video.docx",
        "url": "https://www.youtube.com/watch?v=iV66QbFG1x0",
        "category": "Zone Segmentation",
        "tags": "Zone Segmentation, Segmentation, Network Segmentation, Campus, RTC, Rapid Threat Containment, FTD, Firepower, ISE, Automated Response, Demo Video",
        "product": "Zone Segmentation – Campus RTC with FTD and ISE",
        "description": (
            "Rapid Threat Containment (RTC) with Firepower Threat Defense (FTD) and ISE provides automated threat response "
            "in campus networks. When FTD detects a threat (malware, intrusion, C2 communication), it automatically notifies ISE, "
            "which immediately quarantines the compromised endpoint by changing its SGT assignment or VLAN placement. "
            "This reduces the response time from hours to seconds. The integration supports adaptive network control (ANC) "
            "actions including quarantine, unquarantine, port shutdown, and session termination. "
            "It works across wired and wireless campus networks without manual intervention."
        ),
    },
    {
        "doc_id": 23,
        "filename": "Zone_Seg_DC_ACI_RTC_demo-video.docx",
        "url": "https://www.youtube.com/watch?v=ylYY4-x_YEk",
        "category": "Zone Segmentation",
        "tags": "Zone Segmentation, Segmentation, Network Segmentation, Data Center, DC, ACI, RTC, Rapid Threat Containment, Application Centric Infrastructure, Demo Video",
        "product": "Zone Segmentation – DC ACI with Rapid Threat Containment",
        "description": (
            "Data Center ACI (Application Centric Infrastructure) with Rapid Threat Containment automates security response "
            "within the data center fabric. When Secure Firewall detects malicious activity, it triggers ACI to dynamically "
            "isolate compromised endpoints or microsegments by modifying EPG (Endpoint Group) contracts in real-time. "
            "This leverages ACI's programmable fabric to enforce quarantine at the network level without disrupting "
            "other workloads. The integration provides automated east-west threat containment, reduces blast radius "
            "of breaches, and supports forensic isolation for investigation — all orchestrated through policy-driven automation."
        ),
    },
]


def build_enriched_content(video: dict) -> str:
    """Build enriched document content for a demo video"""
    return f"""{video['category']} | {video['product']}

TAGS: {video['tags']}

OVERVIEW

{video['description']}

DEMO VIDEO

Watch the demonstration video to see {video['product']} in action:

Demo Video: {video['url']}

Source: {video['product']} | Tags: {video['tags']} | {video['url']}"""


def main():
    """Re-ingest all demo video documents with enriched content and metadata"""
    from app.services.rag_service import rag_service

    logger.info("=" * 70)
    logger.info("RE-INGESTING DEMO VIDEO DOCUMENTS")
    logger.info("=" * 70)

    # Step 1: Delete existing demo video chunks
    logger.info("\n--- Step 1: Deleting existing demo video chunks ---")
    for video in ENRICHED_VIDEOS:
        doc_id = video["doc_id"]
        try:
            rag_service.delete_document(doc_id)
            logger.info(f"  Deleted chunks for doc_id={doc_id} ({video['filename']})")
        except Exception as e:
            logger.warning(f"  Could not delete doc_id={doc_id}: {e}")

    # Step 2: Re-ingest with enriched content and proper metadata
    logger.info("\n--- Step 2: Re-ingesting with enriched content ---")
    success = 0
    failed = 0

    for video in ENRICHED_VIDEOS:
        try:
            # Build enriched content
            text = build_enriched_content(video)

            # Build metadata with tags, category, content_type
            metadata = {
                "document_id": video["doc_id"],
                "filename": video["filename"],
                "title": video["product"],
                "tags": video["tags"],
                "category": video["category"],
                "content_type": "demo_video",
                "file_type": "docx",
                "is_public": False,
                "allowed_roles": "",
                "owner_id": 1,
            }

            # Add to vector store (will be kept as single chunk since < 1500 chars)
            chunk_ids = rag_service.add_document(text, metadata)

            logger.info(
                f"  ✅ doc_id={video['doc_id']}: {video['product']} "
                f"({len(text)} chars, {len(chunk_ids)} chunk(s))"
            )
            success += 1

        except Exception as e:
            logger.error(f"  ❌ doc_id={video['doc_id']}: {e}")
            failed += 1

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info(f"DONE: {success} succeeded, {failed} failed out of {len(ENRICHED_VIDEOS)} videos")
    logger.info("=" * 70)

    # Step 3: Verify
    logger.info("\n--- Step 3: Verification ---")
    import chromadb
    from app.core.config import settings
    client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
    col = client.get_collection("langchain")

    for video in ENRICHED_VIDEOS[:3]:  # Spot-check first 3
        results = col.get(
            where={"document_id": video["doc_id"]},
            include=["documents", "metadatas"],
        )
        n = len(results["ids"])
        if n > 0:
            meta = results["metadatas"][0]
            doc_preview = results["documents"][0][:120]
            logger.info(
                f"  doc_id={video['doc_id']}: {n} chunk(s), "
                f"tags_in_meta={'tags' in meta}, "
                f"category={meta.get('category','?')}, "
                f"preview={doc_preview}..."
            )
        else:
            logger.warning(f"  doc_id={video['doc_id']}: NO CHUNKS FOUND!")


if __name__ == "__main__":
    main()
