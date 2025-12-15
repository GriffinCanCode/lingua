from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.etymology import EtymologyNode, EtymologyRelation

router = APIRouter()


class EtymologyNodeCreate(BaseModel):
    word: str
    language: str
    language_period: Optional[str] = None
    part_of_speech: Optional[str] = None
    meaning: Optional[str] = None
    pronunciation: Optional[str] = None
    is_reconstructed: str = "N"
    notes: Optional[str] = None
    source: Optional[str] = None


class EtymologyNodeResponse(BaseModel):
    id: UUID
    word: str
    language: str
    language_period: Optional[str]
    meaning: Optional[str]
    pronunciation: Optional[str]
    is_reconstructed: str

    class Config:
        from_attributes = True


class EtymologyRelationCreate(BaseModel):
    source_id: UUID
    target_id: UUID
    relation_type: str  # cognate, derived_from, borrowed_from, semantic_shift
    confidence: int = 100
    notes: Optional[str] = None
    source: Optional[str] = None


class EtymologyRelationResponse(BaseModel):
    id: UUID
    source_id: UUID
    target_id: UUID
    relation_type: str
    confidence: int

    class Config:
        from_attributes = True


class WordFamilyNode(BaseModel):
    id: UUID
    word: str
    language: str
    meaning: Optional[str]
    is_reconstructed: str


class WordFamilyEdge(BaseModel):
    source: UUID
    target: UUID
    relation_type: str
    confidence: int


class WordFamilyResponse(BaseModel):
    nodes: list[WordFamilyNode]
    edges: list[WordFamilyEdge]


@router.post("/nodes", response_model=EtymologyNodeResponse)
async def create_node(node_data: EtymologyNodeCreate, db: AsyncSession = Depends(get_db)):
    node = EtymologyNode(**node_data.model_dump())
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


@router.get("/nodes/{node_id}", response_model=EtymologyNodeResponse)
async def get_node(node_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EtymologyNode).where(EtymologyNode.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Etymology node not found")
    return node


@router.get("/search", response_model=list[EtymologyNodeResponse])
async def search_nodes(
    word: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(EtymologyNode)
    if word:
        query = query.where(EtymologyNode.word.ilike(f"%{word}%"))
    if language:
        query = query.where(EtymologyNode.language == language)
    query = query.limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/relations", response_model=EtymologyRelationResponse)
async def create_relation(rel_data: EtymologyRelationCreate, db: AsyncSession = Depends(get_db)):
    relation = EtymologyRelation(**rel_data.model_dump())
    db.add(relation)
    await db.commit()
    await db.refresh(relation)
    return relation


@router.get("/word-family/{node_id}", response_model=WordFamilyResponse)
async def get_word_family(
    node_id: UUID,
    depth: int = Query(2, ge=1, le=5),
    db: AsyncSession = Depends(get_db),
):
    """Get the word family graph for a node (cognates, derivations, etc.)
    
    Uses recursive CTE to traverse the etymology graph.
    """
    # Start with the root node
    result = await db.execute(select(EtymologyNode).where(EtymologyNode.id == node_id))
    root = result.scalar_one_or_none()
    if not root:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Collect nodes and edges via breadth-first traversal
    visited_ids = {node_id}
    nodes = [WordFamilyNode(
        id=root.id,
        word=root.word,
        language=root.language,
        meaning=root.meaning,
        is_reconstructed=root.is_reconstructed,
    )]
    edges = []
    
    current_ids = {node_id}
    for _ in range(depth):
        if not current_ids:
            break
        
        # Find all relations involving current nodes
        result = await db.execute(
            select(EtymologyRelation).where(
                or_(
                    EtymologyRelation.source_id.in_(current_ids),
                    EtymologyRelation.target_id.in_(current_ids),
                )
            )
        )
        relations = result.scalars().all()
        
        next_ids = set()
        for rel in relations:
            edges.append(WordFamilyEdge(
                source=rel.source_id,
                target=rel.target_id,
                relation_type=rel.relation_type,
                confidence=rel.confidence,
            ))
            
            # Add newly discovered nodes
            for nid in [rel.source_id, rel.target_id]:
                if nid not in visited_ids:
                    next_ids.add(nid)
                    visited_ids.add(nid)
        
        # Fetch the new nodes
        if next_ids:
            result = await db.execute(
                select(EtymologyNode).where(EtymologyNode.id.in_(next_ids))
            )
            for node in result.scalars().all():
                nodes.append(WordFamilyNode(
                    id=node.id,
                    word=node.word,
                    language=node.language,
                    meaning=node.meaning,
                    is_reconstructed=node.is_reconstructed,
                ))
        
        current_ids = next_ids
    
    return WordFamilyResponse(nodes=nodes, edges=edges)


@router.get("/cognates/{word}", response_model=list[EtymologyNodeResponse])
async def find_cognates(
    word: str,
    source_language: str = Query("ru"),
    db: AsyncSession = Depends(get_db),
):
    """Find cognates of a word across languages"""
    # First find the node for this word
    result = await db.execute(
        select(EtymologyNode).where(
            EtymologyNode.word == word,
            EtymologyNode.language == source_language,
        )
    )
    source_node = result.scalar_one_or_none()
    if not source_node:
        return []
    
    # Find cognate relations
    result = await db.execute(
        select(EtymologyRelation).where(
            EtymologyRelation.relation_type == "cognate",
            or_(
                EtymologyRelation.source_id == source_node.id,
                EtymologyRelation.target_id == source_node.id,
            ),
        )
    )
    relations = result.scalars().all()
    
    # Get the cognate nodes
    cognate_ids = set()
    for rel in relations:
        if rel.source_id != source_node.id:
            cognate_ids.add(rel.source_id)
        if rel.target_id != source_node.id:
            cognate_ids.add(rel.target_id)
    
    if not cognate_ids:
        return []
    
    result = await db.execute(
        select(EtymologyNode).where(EtymologyNode.id.in_(cognate_ids))
    )
    return result.scalars().all()

