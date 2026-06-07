"""CCF venue classification — maps conference abbreviations to CCF levels and metadata."""

from typing import NamedTuple


class VenueInfo(NamedTuple):
    full_name: str
    level: str  # "A" | "B" | "C"
    field: str  # Chinese field label
    ss_venue_name: str  # Exact string for Semantic Scholar venue: filter


CCF_A_VENUES: dict[str, VenueInfo] = {
    "CVPR": VenueInfo(
        "IEEE/CVF Conference on Computer Vision and Pattern Recognition",
        "A", "计算机视觉", "CVPR",
    ),
    "AAAI": VenueInfo(
        "AAAI Conference on Artificial Intelligence",
        "A", "人工智能", "AAAI",
    ),
    "ICCV": VenueInfo(
        "IEEE/CVF International Conference on Computer Vision",
        "A", "计算机视觉", "ICCV",
    ),
    "NeurIPS": VenueInfo(
        "Conference on Neural Information Processing Systems",
        "A", "机器学习", "NeurIPS",
    ),
    "ICML": VenueInfo(
        "International Conference on Machine Learning",
        "A", "机器学习", "ICML",
    ),
    "ACL": VenueInfo(
        "Annual Meeting of the Association for Computational Linguistics",
        "A", "自然语言处理", "ACL",
    ),
    "SIGIR": VenueInfo(
        "International ACM SIGIR Conference on Research and Development in Information Retrieval",
        "A", "信息检索", "SIGIR",
    ),
    "WWW": VenueInfo(
        "The Web Conference",
        "A", "互联网与数据挖掘", "WWW",
    ),
    "SIGMOD": VenueInfo(
        "ACM SIGMOD International Conference on Management of Data",
        "A", "数据库", "SIGMOD",
    ),
    "SIGCOMM": VenueInfo(
        "ACM SIGCOMM Conference",
        "A", "计算机网络", "SIGCOMM",
    ),
    "OSDI": VenueInfo(
        "USENIX Symposium on Operating Systems Design and Implementation",
        "A", "操作系统", "OSDI",
    ),
    "SOSP": VenueInfo(
        "ACM Symposium on Operating Systems Principles",
        "A", "操作系统", "SOSP",
    ),
    "PLDI": VenueInfo(
        "ACM SIGPLAN Conference on Programming Language Design and Implementation",
        "A", "编程语言", "PLDI",
    ),
    "POPL": VenueInfo(
        "ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages",
        "A", "编程语言", "POPL",
    ),
    "ICSE": VenueInfo(
        "International Conference on Software Engineering",
        "A", "软件工程", "ICSE",
    ),
    "STOC": VenueInfo(
        "ACM Symposium on Theory of Computing",
        "A", "计算理论", "STOC",
    ),
    "FOCS": VenueInfo(
        "IEEE Symposium on Foundations of Computer Science",
        "A", "计算理论", "FOCS",
    ),
    "MOBICOM": VenueInfo(
        "ACM International Conference on Mobile Computing and Networking",
        "A", "移动计算", "MobiCom",
    ),
    "CCS": VenueInfo(
        "ACM Conference on Computer and Communications Security",
        "A", "网络安全", "CCS",
    ),
    "S&P": VenueInfo(
        "IEEE Symposium on Security and Privacy",
        "A", "网络安全", "S&P",
    ),
    "CRYPTO": VenueInfo(
        "International Cryptology Conference",
        "A", "密码学", "CRYPTO",
    ),
}

CCF_B_VENUES: dict[str, VenueInfo] = {
    "ECCV": VenueInfo(
        "European Conference on Computer Vision",
        "B", "计算机视觉", "ECCV",
    ),
    "ICRA": VenueInfo(
        "IEEE International Conference on Robotics and Automation",
        "B", "机器人", "ICRA",
    ),
    "EMNLP": VenueInfo(
        "Conference on Empirical Methods in Natural Language Processing",
        "B", "自然语言处理", "EMNLP",
    ),
    "NAACL": VenueInfo(
        "Annual Conference of the North American Chapter of the ACL",
        "B", "自然语言处理", "NAACL",
    ),
    "COLING": VenueInfo(
        "International Conference on Computational Linguistics",
        "B", "自然语言处理", "COLING",
    ),
    "ICLR": VenueInfo(
        "International Conference on Learning Representations",
        "B", "机器学习", "ICLR",
    ),
    "UAI": VenueInfo(
        "Conference on Uncertainty in Artificial Intelligence",
        "B", "人工智能", "UAI",
    ),
    "AISTATS": VenueInfo(
        "International Conference on Artificial Intelligence and Statistics",
        "B", "机器学习", "AISTATS",
    ),
    "COLT": VenueInfo(
        "Annual Conference on Learning Theory",
        "B", "计算学习理论", "COLT",
    ),
    "CIKM": VenueInfo(
        "ACM International Conference on Information and Knowledge Management",
        "B", "数据挖掘", "CIKM",
    ),
    "WSDM": VenueInfo(
        "ACM International Conference on Web Search and Data Mining",
        "B", "数据挖掘", "WSDM",
    ),
    "MM": VenueInfo(
        "ACM International Conference on Multimedia",
        "B", "多媒体", "MM",
    ),
    "IROS": VenueInfo(
        "IEEE/RSJ International Conference on Intelligent Robots and Systems",
        "B", "机器人", "IROS",
    ),
    "ISCA": VenueInfo(
        "International Conference on Computer Architecture",
        "B", "计算机体系结构", "ISCA",
    ),
    "MICRO": VenueInfo(
        "IEEE/ACM International Symposium on Microarchitecture",
        "B", "计算机体系结构", "MICRO",
    ),
    "HPCA": VenueInfo(
        "IEEE International Symposium on High-Performance Computer Architecture",
        "B", "计算机体系结构", "HPCA",
    ),
    "ASE": VenueInfo(
        "IEEE/ACM International Conference on Automated Software Engineering",
        "B", "软件工程", "ASE",
    ),
    "ISSTA": VenueInfo(
        "ACM SIGSOFT International Symposium on Software Testing and Analysis",
        "B", "软件工程", "ISSTA",
    ),
    "RTSS": VenueInfo(
        "IEEE Real-Time Systems Symposium",
        "B", "实时系统", "RTSS",
    ),
}

ALL_CCF_VENUES: dict[str, VenueInfo] = {**CCF_A_VENUES, **CCF_B_VENUES}


def get_venue_info(key: str) -> VenueInfo | None:
    """Look up a venue by its abbreviation key."""
    return ALL_CCF_VENUES.get(key)
