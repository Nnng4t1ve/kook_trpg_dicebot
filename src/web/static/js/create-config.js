/**
 * COC7 角色卡创建器 - 配置常量
 */

// 属性配置
const ATTRIBUTES = {
    str: { name: 'STR 力量', formula: '3D6×5', roll: '3d6' },
    con: { name: 'CON 体质', formula: '3D6×5', roll: '3d6' },
    siz: { name: 'SIZ 体型', formula: '(2D6+6)×5', roll: '2d6+6' },
    dex: { name: 'DEX 敏捷', formula: '3D6×5', roll: '3d6' },
    app: { name: 'APP 外貌', formula: '3D6×5', roll: '3d6' },
    int: { name: 'INT 智力', formula: '(2D6+6)×5', roll: '2d6+6' },
    pow: { name: 'POW 意志', formula: '3D6×5', roll: '3d6' },
    edu: { name: 'EDU 教育', formula: '(2D6+6)×5', roll: '2d6+6' },
    luk: { name: 'LUK 幸运', formula: '3D6×5', roll: '3d6', noCheckbox: true }
};

const ATTR_IDS = Object.keys(ATTRIBUTES);

// 体格/伤害加值表
const BUILD_DB_TABLE = [
    { max: 64, build: -2, db: '-2' },
    { max: 84, build: -1, db: '-1' },
    { max: 124, build: 0, db: '0' },
    { max: 164, build: 1, db: '+1d4' },
    { max: 204, build: 2, db: '+1d6' },
    { max: 284, build: 3, db: '+2d6' },
    { max: 364, build: 4, db: '+3d6' },
    { max: Infinity, build: 5, db: '+4d6' }
];

// 背景故事字段配置
const BACKSTORY_FIELDS = [
    { name: 'appearance', label: '形象描述', placeholder: '描述角色的外貌特征...' },
    { name: 'ideology', label: '思想与信念', placeholder: '角色的信仰、价值观...' },
    { name: 'significant_people', label: '重要之人', placeholder: '对角色重要的人...' },
    { name: 'meaningful_locations', label: '意义非凡之地', placeholder: '对角色有特殊意义的地点...' },
    { name: 'treasured_possessions', label: '宝贵之物', placeholder: '角色珍视的物品...' },
    { name: 'traits', label: '特质', placeholder: '角色的性格特点...' },
    { name: 'injuries', label: '伤口和伤疤', placeholder: '角色身上的伤痕...' },
    { name: 'phobias', label: '恐惧症和躁狂症', placeholder: '角色的恐惧或狂躁...' }
];

// 物品栏行数
const INVENTORY_ROWS = 10;
