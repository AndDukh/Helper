#!/bin/bash

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

current_branch="$(git branch --show-current)"

if [[ -z "${current_branch}" ]]; then
    echo -e "${YELLOW}Не удалось определить текущую ветку.${NC}"
    exit 1
fi

echo -e "${BLUE}📦 Добавляем изменения...${NC}"
git add .

if git diff --cached --quiet; then
    echo -e "${YELLOW}Нет изменений для коммита.${NC}"
    exit 0
fi

echo -e "${BLUE}💾 Создаём коммит...${NC}"
git commit -m "auto: $(date '+%Y-%m-%d %H:%M:%S')"

echo -e "${BLUE}🚀 Пушим на GitHub...${NC}"
git push origin "${current_branch}"

echo -e "${GREEN}✅ Отправлено. Если Railway подключён к этой ветке GitHub, деплой начнётся автоматически через 10-30 секунд.${NC}"
