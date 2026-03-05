import { cn, formatDateTime } from '@/lib/utils';
import { User, Bot } from 'lucide-react';

const ChatMessage = ({ message, isUser }) => {
  return (
    <div
      className={cn(
        'flex gap-3 animate-slide-up',
        isUser && 'flex-row-reverse'
      )}
    >
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
          isUser ? 'bg-primary-600' : 'bg-gray-600'
        )}
      >
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-white" />
        )}
      </div>
      <div
        className={cn(
          'flex flex-col gap-1 max-w-[70%]',
          isUser && 'items-end'
        )}
      >
        <div
          className={cn(
            'px-4 py-2 rounded-lg',
            isUser
              ? 'bg-primary-600 text-white rounded-tr-none'
              : 'bg-gray-100 text-gray-900 rounded-tl-none'
          )}
        >
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
        {message.timestamp && (
          <span className="text-xs text-gray-500 px-1">
            {formatDateTime(message.timestamp)}
          </span>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
