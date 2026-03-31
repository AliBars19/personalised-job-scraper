"""Filter scraped jobs by relevance to hospitality management and wine roles."""

from __future__ import annotations

import re

# Title keywords that strongly indicate a relevant role
STRONG_TITLE_KEYWORDS = re.compile(
    r"(restaurant|hotel|hospitality|food.{0,3}beverage|f&b|f\s*&\s*b"
    r"|front.?of.?house|foh|banquet|catering|bar\s|bar.?manager"
    r"|pub\s|pub.?manager|chef|kitchen|concierge|housekeep"
    r"|reception(?:ist)?|sommelier|wine|cellar|vineyard|beverage"
    r"|head.?waiter|maitre|brasserie|bistro|cafe|coffee.?shop"
    r"|cocktail|mixologist|pastry|sous.?chef|commis|porter"
    r"|night.?manager|wedding|private.?dining|members.?club"
    r"|supper.?club|tavern|inn\s|grill|steakhouse|pizz"
    r"|room.?attendant|reservations|guest.?relation|spa.?manager"
    r"|leisure.?manager|breakfast.?manager|back.?of.?house"
    r"|lounge.?manager|floor.?manager)",
    re.IGNORECASE,
)

# Generic manager titles that are relevant ONLY if company is hospitality
GENERIC_MANAGER_TITLES = re.compile(
    r"^(general.?manager|assistant.?manager|deputy.?manager"
    r"|duty.?manager|operations.?manager|events.?manager"
    r"|team.?manager|shift.?manager|venue.?manager|club.?manager"
    r"|area.?manager|regional.?manager|senior.?manager"
    r"|assistant.?general.?manager)",
    re.IGNORECASE,
)

# Company names that indicate hospitality/wine industry
HOSPITALITY_COMPANIES = re.compile(
    r"(restaurant|hotel|hospitality|food|beverage|pub|bar|cafe"
    r"|catering|chef|kitchen|wine|sommelier|brasserie|bistro|grill"
    r"|pizza|burger|sushi|noodle|ramen|taco|bbq|bakery|patisserie"
    r"|marriott|hilton|accor|ihg|hyatt|radisson|intercontinental"
    r"|four.?seasons|shangri|mandarin.?oriental|peninsula|corinthia"
    r"|savoy|ritz|claridge|dorchester|soho.?house|ivy|nobu|zuma"
    r"|hawksmoor|dishoom|honest.?burger|flat.?iron|franco.?manca"
    r"|gloria|padella|bao|gymkhana|sketch|chiltern|firehouse"
    r"|wagamama|pret|leon|nando|greggs|starbucks|costa|mcdonald"
    r"|kfc|subway|young.?s|greene.?king|mitchells.?\&.?butler"
    r"|stonegate|ei.?group|punch|star.?pubs|wetherspoon"
    r"|cote|bill.?s|carluccio|prezzo|ask.?italian|zizzi"
    r"|the.?wolseley|scott.?s|j.?sheekey|the.?ivy|le.?caprice"
    r"|majestic.?wine|berry.?bros|laithwaites|naked.?wines"
    r"|berkmann|jeroboams|hedonism|corney.?\&.?barrow"
    r"|noble.?rot|vinoteca|sager.?\+.?wilde|gordon.?ramsay"
    r"|heston|jason.?atherton|angela.?hartnett|marcus.?wareing"
    r"|ledbury|the.?fat.?duck|core.?by|hide.?london"
    r"|compass.?group|sodexo|aramark|elior|levy|baxters"
    r"|etm.?group|d\&d.?london|caprice.?holdings|corbin"
    r"|the.?ned|ham.?yard|hoxton|mondrian|standard"
    r"|edition|aman|rosewood|langham|lanesborough|stafford"
    r"|connaught|beaumont|berkeley|goring|bulgari"
    r"|firmdale|red.?carnation|dorset.?collection"
    r"|lore.?group|ennismore|lhw|leading.?hotels"
    r"|rocco.?forte|jumeirah|kempinski|belmond"
    r"|mi[iï]ro|meliá|melia|tribe|park.?plaza)",
    re.IGNORECASE,
)

# Titles that are NEVER relevant regardless of company
BLACKLISTED_TITLES = re.compile(
    r"(software|developer|engineer|architect|data.?scien|devops"
    r"|accountant|solicitor|lawyer|nurse|doctor|dentist|teacher"
    r"|quantity.?surveyor|plumber|electrician|mechanic"
    r"|care.?worker|support.?worker|social.?worker|nanny"
    r"|personal.?assistant(?!.*hotel)|stockroom|warehouse"
    r"|forklift|driver|cleaner(?!.*hotel)|security.?guard"
    r"|health.?record|ward.?clerk|nursery|childcare"
    r"|marketing.?manager|digital.?manager|seo|ppc"
    r"|financial.?analyst|investment|trading|compliance.?officer"
    r"|hr.?manager|recruitment.?consultant|talent.?acquisition"
    r"|it.?manager|project.?manager|product.?manager"
    r"|street.?works|construction|building|surveyor)",
    re.IGNORECASE,
)


def is_relevant_job(title: str, company: str) -> bool:
    """Return True if the job is relevant to hospitality/wine roles."""
    if not title:
        return False

    combined = f"{title} {company}"

    # Reject blacklisted titles immediately
    if BLACKLISTED_TITLES.search(title):
        return False

    # Strong match — title itself contains hospitality/wine keywords
    if STRONG_TITLE_KEYWORDS.search(title):
        return True

    # Generic manager title — only keep if company is in hospitality
    if GENERIC_MANAGER_TITLES.search(title):
        return bool(HOSPITALITY_COMPANIES.search(company))

    # Check if company name strongly indicates hospitality
    if HOSPITALITY_COMPANIES.search(company):
        # Keep if title is at least management-adjacent
        if re.search(r"manager|supervisor|leader|head\s|director", title, re.IGNORECASE):
            return True

    return False
