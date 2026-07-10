#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

function getSkills(skillsDir) {
  const skills = [];
  if (!fs.existsSync(skillsDir)) return skills;
  
  const entries = fs.readdirSync(skillsDir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.isDirectory()) {
      const skillFile = path.join(skillsDir, entry.name, 'SKILL.md');
      if (fs.existsSync(skillFile)) {
        const content = fs.readFileSync(skillFile, 'utf8');
        const nameMatch = content.match(/name:\s*(.+)/);
        const descMatch = content.match(/description:\s*([\s\S]+?)(?:\n\w+|$)/);
        skills.push({
          name: nameMatch ? nameMatch[1].trim() : entry.name,
          description: descMatch ? descMatch[1].trim() : '',
          path: skillFile
        });
      }
    } else if (entry.name === 'SKILL.md') {
      const content = fs.readFileSync(path.join(skillsDir, entry.name), 'utf8');
      const nameMatch = content.match(/name:\s*(.+)/);
      skills.push({
        name: nameMatch ? nameMatch[1].trim() : 'root-skill',
        description: '',
        path: path.join(skillsDir, entry.name)
      });
    }
  }
  return skills;
}

function runAutoSkill() {
  const args = process.argv.slice(2);
  const promptIndex = args.indexOf('--prompt');
  if (promptIndex === -1 || promptIndex + 1 >= args.length) {
    console.error("Usage: node auto-skill.js --prompt \"your prompt here\"");
    process.exit(1);
  }
  
  const prompt = args[promptIndex + 1].toLowerCase();
  // Assume we are in auto-skill-finder/caveman/bin
  const finderDir = path.resolve(__dirname, '..', '..');
  const skills = getSkills(path.resolve(finderDir, '..')); // Looks at all skills
  
  let bestSkill = null;
  let bestScore = -1;
  
  const promptWords = new Set(prompt.split(/\s+/));
  
  for (const skill of skills) {
    let score = 0;
    const skillWords = new Set((skill.name + ' ' + skill.description).toLowerCase().split(/\s+/));
    for (const w of promptWords) {
      if (skillWords.has(w)) score += 2;
    }
    if (prompt.includes(skill.name.toLowerCase())) score += 10;
    
    if (score > bestScore) {
      bestScore = score;
      bestSkill = skill;
    }
  }
  
  console.log("========================================");
  console.log("AUTO-SKILL FINDER (JS + CAVEMAN)");
  console.log("========================================");
  if (bestSkill && bestScore > 0) {
    console.log(`[MATCH] ${bestSkill.name} (Score: ${bestScore})`);
    console.log(`[PATH] ${bestSkill.path}`);
  } else {
    console.log("[NO MATCH] Fallback to general");
  }
  
  console.log("\n[CAVEMAN MODE ACTIVATED]");
  console.log("Rule: Respond terse like smart caveman. Drop filler. Only technical substance.");
}

runAutoSkill();
