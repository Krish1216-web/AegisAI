import React, { useState, useEffect } from 'react';
import { MessageSquare, Send, Reply, Edit2, Trash2, AtSign, Check, X, CornerDownRight } from 'lucide-react';
import { getComments, createComment, updateComment, deleteComment, getMentionableUsers } from '../../api/comments';

export default function CommentsPanel({ projectId, resourceType, resourceId }) {
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newCommentBody, setNewCommentBody] = useState('');
  const [replyingToId, setReplyingToId] = useState(null);
  const [replyBody, setReplyBody] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editBody, setEditBody] = useState('');
  const [mentionUsers, setMentionUsers] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    if (projectId || (resourceType && resourceId)) {
      loadComments();
      if (projectId) {
        getMentionableUsers(projectId).then(setMentionUsers).catch(() => {});
      }
    }
  }, [projectId, resourceType, resourceId]);

  const loadComments = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const res = await getComments({ project_id: projectId, resource_type: resourceType, resource_id: resourceId });
      setComments(res.comments || []);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load comments');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newCommentBody.trim()) return;
    try {
      await createComment({
        body: newCommentBody,
        project_id: projectId,
        resource_type: resourceType,
        resource_id: resourceId
      });
      setNewCommentBody('');
      loadComments();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to post comment');
    }
  };

  const handleReply = async (parentId) => {
    if (!replyBody.trim()) return;
    try {
      await createComment({
        body: replyBody,
        project_id: projectId,
        resource_type: resourceType,
        resource_id: resourceId,
        parent_comment_id: parentId
      });
      setReplyBody('');
      setReplyingToId(null);
      loadComments();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to post reply');
    }
  };

  const handleEdit = async (commentId) => {
    if (!editBody.trim()) return;
    try {
      await updateComment(commentId, editBody);
      setEditingId(null);
      setEditBody('');
      loadComments();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to edit comment');
    }
  };

  const handleDelete = async (commentId) => {
    try {
      await deleteComment(commentId);
      loadComments();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to delete comment');
    }
  };

  const rootComments = comments.filter(c => !c.parent_comment_id);
  const getReplies = (parentId) => comments.filter(c => c.parent_comment_id === parentId);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-indigo-400" />
          Discussions ({comments.length})
        </h3>
      </div>

      {errorMsg && (
        <div className="bg-red-950/60 border border-red-800 text-red-300 text-xs px-3 py-2 rounded-lg">
          {errorMsg}
        </div>
      )}

      {/* Main Comment Input */}
      <form onSubmit={handleCreate} className="space-y-2">
        <div className="relative">
          <textarea
            placeholder="Add to the discussion... use @username to mention teammates"
            value={newCommentBody}
            onChange={(e) => setNewCommentBody(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm text-white focus:outline-none focus:border-indigo-500"
            rows={3}
          />
        </div>
        <div className="flex justify-end">
          <button
            type="submit"
            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1.5 rounded-lg text-xs font-medium transition"
          >
            <Send className="w-3.5 h-3.5" />
            Comment
          </button>
        </div>
      </form>

      {/* Threaded List */}
      <div className="space-y-4 divide-y divide-gray-800/60">
        {rootComments.map((comment) => (
          <div key={comment.id} className="pt-4 space-y-3">
            <div className="bg-gray-850 border border-gray-800 rounded-lg p-3 space-y-2">
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-xs text-indigo-300">{comment.author_name}</span>
                  <span className="text-[10px] text-gray-500">
                    {new Date(comment.created_at).toLocaleString()}
                    {comment.edited_at && ' (edited)'}
                  </span>
                </div>
                {comment.status === 'active' && (
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => {
                        setEditingId(comment.id);
                        setEditBody(comment.body);
                      }}
                      className="text-gray-500 hover:text-gray-300 p-1 rounded"
                      title="Edit"
                    >
                      <Edit2 className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => handleDelete(comment.id)}
                      className="text-gray-500 hover:text-red-400 p-1 rounded"
                      title="Delete"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                )}
              </div>

              {editingId === comment.id ? (
                <div className="space-y-2">
                  <textarea
                    value={editBody}
                    onChange={(e) => setEditBody(e.target.value)}
                    className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-xs text-white"
                    rows={2}
                  />
                  <div className="flex justify-end gap-1.5">
                    <button
                      onClick={() => setEditingId(null)}
                      className="px-2 py-1 text-xs text-gray-400 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleEdit(comment.id)}
                      className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs"
                    >
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <p className={`text-xs ${comment.status === 'deleted' ? 'text-gray-500 italic' : 'text-gray-200'}`}>
                  {comment.body}
                </p>
              )}

              {comment.status === 'active' && (
                <div className="flex items-center gap-3 pt-1">
                  <button
                    onClick={() => {
                      setReplyingToId(replyingToId === comment.id ? null : comment.id);
                      setReplyBody('');
                    }}
                    className="text-[11px] text-gray-400 hover:text-indigo-400 flex items-center gap-1 transition"
                  >
                    <Reply className="w-3 h-3" />
                    Reply
                  </button>
                </div>
              )}
            </div>

            {/* Reply Input Box */}
            {replyingToId === comment.id && (
              <div className="ml-6 space-y-2">
                <textarea
                  placeholder="Write a reply..."
                  value={replyBody}
                  onChange={(e) => setReplyBody(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  rows={2}
                />
                <div className="flex justify-end gap-1.5">
                  <button
                    onClick={() => setReplyingToId(null)}
                    className="px-2 py-1 text-xs text-gray-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleReply(comment.id)}
                    className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs font-medium"
                  >
                    Post Reply
                  </button>
                </div>
              </div>
            )}

            {/* Nested Replies */}
            {getReplies(comment.id).map((reply) => (
              <div key={reply.id} className="ml-6 bg-gray-900 border border-gray-800/80 rounded-lg p-3 space-y-1.5">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-1.5">
                    <CornerDownRight className="w-3 h-3 text-indigo-400" />
                    <span className="font-medium text-xs text-indigo-300">{reply.author_name}</span>
                    <span className="text-[10px] text-gray-500">{new Date(reply.created_at).toLocaleString()}</span>
                  </div>
                  {reply.status === 'active' && (
                    <button
                      onClick={() => handleDelete(reply.id)}
                      className="text-gray-500 hover:text-red-400 p-0.5 rounded"
                      title="Delete"
                    >
                      <Trash2 className="w-2.5 h-2.5" />
                    </button>
                  )}
                </div>
                <p className={`text-xs ${reply.status === 'deleted' ? 'text-gray-500 italic' : 'text-gray-300'}`}>
                  {reply.body}
                </p>
              </div>
            ))}
          </div>
        ))}

        {rootComments.length === 0 && !loading && (
          <div className="text-center py-8 text-gray-500 text-xs">No comments yet. Start the conversation!</div>
        )}
      </div>
    </div>
  );
}
