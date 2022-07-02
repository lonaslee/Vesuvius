from __future__ import annotations

import asyncio
import re
import datetime
from collections import namedtuple
from math import radians
from random import randint
from typing import Literal

import discord
from aiofiles import open as aopen
from discord import ui
from discord import app_commands
from discord.ext import commands

from extensions.transformations import AllPoints
from extensions.definitions import ANSIColors as C, NUM_EMOTES


class BaseSquare:
    """Base class for a square on any board."""

    def __init__(self) -> None:
        self.occupier: Literal['1', '2', '0'] = '0'


class BaseBoard:
    """Base class for a game board.

    Methods
    -------
    __str__

    to_emojis

    is_valid_square

    set_square

    check_win
    """

    def __init__(
        self,
        p1_emoji: str,
        p2_emoji: str,
        empty_emoji: str,
        length: int,
        square_type: type[BaseSquare],
    ) -> None:
        """Initialize a board."""
        self.p1_emoji = p1_emoji
        self.p2_emoji = p2_emoji
        self.no_emoji = empty_emoji
        self.length = length
        self.square_type = square_type
        self._all_squares: list[BaseSquare] = [
            self.square_type() for _ in range(self.length * self.length)
        ]

    def __str__(self) -> str:
        return '\n'.join(
            reversed(
                [
                    ''.join([square.occupier for square in square_slice])
                    for square_slice in [
                        self._all_squares[i : i + self.length]
                        for i in range(0, self.length * self.length, self.length)
                    ]
                ]
            )
        )

    async def to_emojis(self) -> str:
        """Convert to discord emojis.

        This returns a string version of the board ready to be sent directly to discord.
        """
        return (
            str(self)
            .replace('1', self.p1_emoji)
            .replace('2', self.p2_emoji)
            .replace('0', self.no_emoji)
        )

    async def is_valid_square(self, x: int, y: int, value: str) -> bool:
        """Check if a player can place a piece in x, y.

        x and y are not compared to the size of the board,
        this will raise IndexError if they are too big.

        By default this decides based on whether the spot is empty, but
        it can be overriden for special games.
        """
        if self._all_squares[self.length * y - self.length + x - 1].occupier == '0':
            return True
        return False

    async def set_square(self, x: int, y: int, value: Literal['1', '2']) -> None:
        """Set a square to a new value.

        This assumes that setting the square does not break any game rules,
        and that x and y are within the board range.
        """
        self._all_squares[self.length * y - self.length + x - 1].occupier = value

    async def check_win(self) -> Literal['0', '1', '2'] | None:
        """Check for a winner on the board.

        This method is game specific, override in subclasses.
        """
        pass


class PromptMessage:
    """Represents a message asking players to send input."""

    def __init__(self, message: discord.Message) -> None:
        self.message = message

    async def update(self, this_turn: Player) -> None:
        self.message = await self.message.edit(
            content=f'{this_turn.mention} '
            f"{this_turn.symbol}'s turn! (send coordinates)"
        )

    async def winner(
        self,
        this_turn: Player,
        *,
        points_ratio: tuple[int, int] = (0, 0),
        time_is_out: bool = False,
        draw: bool = False,
    ) -> None:
        print(f'call with', this_turn, points_ratio)
        ratio: str = C.E
        timeout: str = C.B + C.YELLOW
        if points_ratio != (0, 0):
            ratio = (
                f' {C.CYAN}{points_ratio[0]}{C.YELLOW}:{C.CYAN}{points_ratio[1]}{C.E}'
            )
        if time_is_out:
            timeout = f"{C.B}{C.YELLOW} Time's up - "
        winner = f'Winner is {this_turn.symbol}, {this_turn}.'
        if draw:
            winner = 'Draw!'
        self.message = await self.message.edit(content=f'{timeout}{winner}{ratio}')

    async def draw(self) -> None:
        self.message = await self.message.edit(content=f'{C.B}{C.YELLOW}draw!{C.E}')

    async def occupied(self, this_turn: Player) -> None:
        self.message = await self.message.edit(
            content=f'{this_turn.mention} '
            'that spot is already occupied. pick another spot'
        )

    async def invalid(self, this_turn: Player) -> None:
        self.message = await self.message.edit(
            content=f'{this_turn.mention} invalid spot. try another place'
        )

    async def timeout(self, this_turn: Player, not_this_turn: Player) -> None:
        self.message = await self.message.edit(
            content=f'{C.B}{C.RED}game ended.{C.YELLOW} '
            f'{not_this_turn} is winner, because {this_turn} took too long.{C.E}'
        )

    async def end_request(self, this_turn: Player, not_this_turn: Player) -> None:
        self.message = await self.message.edit(
            content=f'{not_this_turn.mention} your opponent wants to end the game now. '
            f'respond with "yes" if you agree, or say no to continue'
        )

    async def continue_game(self, this_turn: Player) -> None:
        self.message = await self.message.edit(
            content=f'{this_turn.mention} '
            'your opponent wants to continue! (send coordinates)'
        )

    async def hurry(self, this_turn: Player) -> None:
        self.message = await self.message.edit(content=f'{this_turn.mention} hurry up!')

    async def fmt_error(self, this_turn: Player) -> None:
        self.message = await self.message.edit(
            content=f'{this_turn.mention} '
            'off board range or incorrect format. try again'
        )


class BoardMessage:
    """Represents a message with a stringified `BaseBoard`."""

    def __init__(
        self, message: discord.Message | list[discord.Message], board: BaseBoard
    ) -> None:
        self.message = message
        self.board = board

    async def update(self) -> None:
        if isinstance(self.message, discord.Message):
            if self.message.embeds:
                self.message = await self.message.edit(
                    embeds=await self.board.to_emojis()
                )
                return None
            self.message = await self.message.edit(content=await self.board.to_emojis())
            return None
        for k, v in enumerate(await self.board.to_emojis()):
            self.message[k] = await self.message[k].edit(content=v)


class Player:
    """Represents a player."""

    def __init__(self, m: discord.Member) -> None:
        self.member = m
        self.mention = m.mention

        self.symbol: str = ''
        self.number: str = ''
        self.color: str = ''

    def __str__(self) -> str:
        return self.member.display_name


class BaseGame:
    """Base class for any game.

    Methods
    -------
    start

    _loop_begin

    _iter_begin

    _iter_end

    _timeout

    _end

    _loop_end

    _flush_channel

    _check_board_win

    _get_coord
    """

    def __init__(
        self,
        ctx: commands.Context,
        bot: commands.Bot,
        opponent: discord.Member,
        board_type: type[BaseBoard],
        symbol1: str,
        symbol2: str,
        color1: str,
        color2: str,
        numof_loops: int,
        input_regex: str,
        input_wait_time: int,
    ) -> None:
        """Initalize the game."""
        self.winner: discord.Member = None
        self.loser: discord.Member = None
        self.tie: bool = False

        self._ctx = ctx
        self._bot = bot
        self._board: type[BaseBoard] = board_type()
        self._board_msg: BoardMessage = None
        self._prompt_msg: PromptMessage = None

        self._numof_loops = numof_loops
        self._input_regex = input_regex
        self._wait_time = input_wait_time
        self._input_occupied_error = 'occupied'
        self._input_format_error = 'fmt_error'
        self._flush = False

        self._player1 = Player(ctx.author)
        self._player2 = Player(opponent)

        if randint(0, 1):
            self._player1, self._player2 = self._player2, self._player1

        self._player1.number, self._player2.number = '1', '2'
        self._player1.symbol, self._player2.symbol = symbol1, symbol2
        self._player1.color, self._player2.color = color1, color2

    async def start(self) -> None:
        """Start the game.

        This sends the prompt message and starts the input loop. When the game
        finishes, the `winner`, `loser`, and `tie` attributes will be set accordingly.

        In the event of a tie, the `winner` and `loser` attribute names do not matter.

        Order of calls:
        ---------------
        _loop_begin

        _iter_begin

        _get_coord

        if _timeout

        if _end

        _board.set_square

        _iter_end

        _loop_end
        """
        if await self._loop_begin():
            return None
        this_turn, next_turn = self._player2, self._player1
        for _ in range(self._numof_loops):
            this_turn, next_turn = next_turn, this_turn

            if await self._iter_begin(this_turn, next_turn):
                return None

            x, y = await self._get_coord(this_turn, next_turn)
            if x == 'timeout':
                await self._timeout(this_turn, next_turn)
                return None
            if x == 'end':
                await self._end(this_turn, next_turn)
                return None

            await self._board.set_square(x, y, this_turn.number)
            if await self._iter_end(this_turn, next_turn):
                return None
        await self._loop_end(this_turn, next_turn)
        return None

    async def _loop_begin(self) -> bool:
        """Called before the input loop starts.

        This method is responsble for sending information about which player is what color,
        sending the prompt message and setting `self._prompt_msg`, and sending the
        board message and setting `self._board_msg`

        If this method returns True, the game will exit.
        """
        await self._ctx.send(
            f'{C.B}{self._player1.color}{self._player1.symbol}: {self._player1}, '
            f'{self._player2.color}{self._player2.symbol}: {self._player2}{C.E}'
        )
        self._board_msg = BoardMessage(
            await self._ctx.send(await self._board.to_emojis()), self._board
        )
        self._prompt_msg = PromptMessage(
            await self._ctx.send(
                f"{self._player1.mention} {self._player1.symbol}'s turn!"
            )
        )
        return False

    async def _iter_begin(self, this_turn: Player, next_turn: Player) -> bool:
        """Called at the start of every iteration.

        This method is responsible for calling `update` on the prompt message.

        If this method returns True, the game will exit.
        """
        await self._prompt_msg.update(this_turn)
        return False

    async def _iter_end(self, this_turn: Player, next_turn: Player) -> bool:
        """Called at the end of every iteration of the input loop, after a
        `BaseBoard.set_square` call.

        This method is responsible for calling `update` on the board message, win
        checking with `self._check_board_win`, and flushing the channel with
        `self._flush_channel` if `self._flush` is True.

        If the method returns True, the game will exit.
        """
        if self._flush:
            self._flush = False
            await self._flush_channel()

        await self._board_msg.update()
        if await self._check_board_win(this_turn, next_turn):
            return True
        return False

    async def _timeout(self, this_turn: Player, next_turn: Player) -> None:
        """Called when this turn's player times out."""
        self.winner = next_turn.member
        self.loser = this_turn.member

    async def _end(self, this_turn: Player, next_turn: Player) -> None:
        """Called when an end request is accepted."""
        await self._check_board_win(this_turn, next_turn, force=True)

    async def _loop_end(self, this_turn: Player, next_turn: Player) -> None:
        """Called when the input loop exits.

        By default this sets the attribute `tie` to True,
        override this for different behavior.
        """
        self.winner = this_turn.member
        self.loser = next_turn.member
        self.tie = True

    async def _check_board_win(
        self, this_turn: Player, next_turn: Player, *, force: bool = False
    ) -> bool:
        """Called after every move, and called with `force=True` during end requests.

        By default this sets the attribute `winner` to the player of the current turn,
        override this for different behavior.
        """
        if await self._board.check_win() != '0' or force:
            await self._prompt_msg.winner(this_turn)
            self.winner = this_turn.member
            self.loser = next_turn.member
            return True
        if force:
            await self._prompt_msg.draw()
            self.winner = this_turn.member
            self.loser = next_turn.member
            self.tie = True
            return True
        return False

    async def _flush_channel(self) -> None:
        async for msg in self._prompt_msg.message.channel.history(limit=10):
            if msg == self._prompt_msg.message:
                return None
            await msg.delete()

    async def _get_coord(
        self, this_turn: Player, next_turn: Player
    ) -> tuple[int, int] | tuple[str, None]:
        """Get a coordinate x, y from the current player.

        This users `self._input_regex` to validate the user message,
        `self._board.is_valid_square` to validate spot availiblity, and
        waits `self._wait_time` seconds for every input. If the
        input is not correct or forbidden by the game rules, the prompt message is
        edited accordingly and will ask for another input.

        * On timeout, return tuple[Literal['timeout'], None]
        * On end request, return tuple[Literal['end'], None]
        """
        timeout = end = flush = False

        def check(m: discord.Message):
            if m.content == 'fflush' and m.author in {
                this_turn.member,
                next_turn.member,
            }:
                self._flush = True
                return False
            if m.content.startswith('//'):
                return False
            if end:
                return m.author == next_turn.member and m.channel == self._ctx.channel
            return m.author == this_turn.member and m.channel == self._ctx.channel

        while True:
            if flush:
                async for msg in self._prompt_msg.message.channel.history(limit=10):
                    if msg == self._prompt_msg.message:
                        break
                    await msg.delete()

            try:
                message = await self._bot.wait_for(
                    'message', check=check, timeout=self._wait_time
                )
                await message.delete()
                timeout = False
                x, y = re.search(self._input_regex, message.content).groups()
                x, y = int(x), int(y)

                if not await self._board.is_valid_square(x, y, this_turn.number):
                    await getattr(self._prompt_msg, self._input_occupied_error)(
                        this_turn
                    )
                    continue

                return x, y
            except asyncio.TimeoutError:
                if timeout:
                    await self._prompt_msg.timeout(this_turn, next_turn)
                    return 'timeout', None
                timeout = True
                await self._prompt_msg.hurry(this_turn)
                continue
            except AttributeError:
                if end:
                    if message.content.lower() in {'yes', 'ye', 'ok', 'k'}:
                        return 'end', None
                    else:
                        await self._prompt_msg.continue_game(this_turn)
                        end = False
                        continue

                if 'end' in message.content.lower():
                    end = True
                    await self._prompt_msg.end_request(this_turn, next_turn)
                    continue

                await getattr(self._prompt_msg, self._input_format_error)(this_turn)
                continue


# subclasses ===========================================================================


class TicTacToeSquare(BaseSquare):
    pass


class TicTacToeBoard(BaseBoard):
    def __init__(self) -> None:
        super().__init__(':x:', ':o:', ':question:', 3, TicTacToeSquare)

    async def check_win(self) -> Literal['0', 'y']:
        anylst = [
            self._all_equal(ls)
            for ls in [self._all_squares[i : i + 3] for i in (0, 3, 6)]
        ]
        anylst.append(self._all_equal([self._all_squares[i] for i in (0, 4, 8)]))
        anylst.append(self._all_equal([self._all_squares[i] for i in (2, 4, 6)]))
        if any(anylst):
            return 'y'
        return '0'

    @staticmethod
    def _all_equal(ls) -> bool:
        return (
            ls[0].occupier != '0' and ls[0].occupier == ls[1].occupier == ls[2].occupier
        )


class TicTacToeGame(BaseGame):
    def __init__(
        self, ctx: commands.Context, bot: commands.Bot, opponent: discord.Member
    ) -> None:
        super().__init__(
            ctx,
            bot,
            opponent,
            TicTacToeBoard,
            'X',
            'O',
            C.RED,
            C.RED,
            9,
            r'(?P<x>[1-3])[, ]*(?P<y>[1-3])',
            30,
        )


class ConnectFourSquare(BaseSquare):
    pass


class ConnectFourBoard(BaseBoard):
    def __init__(self) -> None:
        self.p1_emoji = '🟡'
        self.p2_emoji = '🔴'
        self.no_emoji = '⚫'
        self.length = 7
        self.square_type = ConnectFourSquare
        self._all_squares: list[BaseSquare] = [
            self.square_type() for _ in range(self.length * 6)
        ]

        self.rows = [self._all_squares[k - 7 : k] for k in range(7, 43, 7)]
        self.columns = [
            [l[n] for l in self.rows] for n in range(7)
        ]  # the columns are actually work correctly with [x][y] indexings
        self.right_diagonals = [
            [(0, 2)],
            [(0, 1)],
            [(0, 0)],
            [(1, 0)],
            [(2, 0)],
            [(3, 0)],
        ]
        self.left_diagonals = [
            [(0, 3)],
            [(0, 4)],
            [(0, 5)],
            [(1, 5)],
            [(2, 5)],
            [(3, 5)],
        ]
        for n in range(1, 7):
            for right_list in self.right_diagonals:
                try:
                    right_list.append(
                        self.columns[right_list[0][0] + n][right_list[0][1] + n]
                    )
                except IndexError:
                    pass
            for left_list in self.left_diagonals:
                try:
                    left_list.append(
                        self.columns[left_list[0][0] + n][left_list[0][1] - n]
                    )
                except IndexError:
                    pass

        for diag_list in self.right_diagonals:
            diag_list[0] = self.columns[diag_list[0][0]][diag_list[0][1]]
        for diag_list in self.left_diagonals:
            diag_list[0] = self.columns[diag_list[0][0]][diag_list[0][1]]

    async def to_emojis(self):
        string = str(self).splitlines(keepends=True)
        return ''.join(string[0:4]).replace('1', '🟡').replace('2', '🔴').replace(
            '0', '⚫'
        ), ''.join(string[4:7]).replace('1', '🟡').replace('2', '🔴').replace('0', '⚫')

    async def is_valid_square(self, x: int, y: int, value: str) -> bool:
        # since there is gravity we don't have to worry about y
        if not [
            square for square in self.columns[int(x) - 1] if square.occupier == '0'
        ]:
            return False
        return True

    async def set_square(self, x: int, y: int, value: Literal['1', '2']) -> None:
        this_column = [
            square for square in self.columns[int(x) - 1] if square.occupier == '0'
        ]
        this_column[0].occupier = value

    async def check_win(self) -> Literal['y', '0']:
        for lst in (self.rows, self.columns, self.right_diagonals, self.left_diagonals):
            for some_row in [
                ''.join(sl) for sl in [[p.occupier for p in l] for l in lst]
            ]:
                if some_row.find('1111') != -1:
                    return 'y'
                if some_row.find('2222') != -1:
                    return 'y'
        return '0'


class ConnectFourGame(BaseGame):
    def __init__(
        self, ctx: commands.Context, bot: commands.Bot, opponent: discord.Member
    ) -> None:
        super().__init__(
            ctx,
            bot,
            opponent,
            ConnectFourBoard,
            'Yellow',
            'Red',
            C.YELLOW,
            C.RED,
            42,
            None,
            30,
        )

    async def _loop_begin(self) -> bool:
        await self._ctx.send(
            f'{C.B}{self._player1.color}{self._player1.symbol}: {self._player1}, '
            f'{self._player2.color}{self._player2.symbol}: {self._player2}{C.E}'
        )
        board1, board2 = await self._board.to_emojis()
        msg1 = await self._ctx.send(board1)
        msg2 = await self._ctx.send(board2)
        self._board_msg = BoardMessage([msg1, msg2], self._board)
        for num in NUM_EMOTES[:7]:
            await self._board_msg.message[1].add_reaction(num)

        self._prompt_msg = PromptMessage(
            await self._ctx.send(
                f"{self._player1.mention} {self._player1.symbol}'s turn!"
            )
        )
        return False

    async def _get_coord(
        self, this_turn: Player, next_turn: Player
    ) -> tuple[int, None]:
        def check(reaction: discord.Reaction, user: discord.User):
            return (
                user.id == this_turn.member.id
                and reaction.message == self._board_msg.message[1]
                and str(reaction.emoji) in NUM_EMOTES[:7]
            )

        timeout = False
        while True:
            try:
                reaction, user = await self._bot.wait_for(
                    'reaction_add', check=check, timeout=self._wait_time
                )
                await reaction.remove(user)

                for k, num in enumerate(NUM_EMOTES):
                    if num == str(reaction.emoji):
                        if not await self._board.is_valid_square(k + 1, 0, None):
                            await self._prompt_msg.occupied(this_turn)
                            continue
                        return k + 1, None
            except asyncio.TimeoutError:
                if timeout:
                    await self._prompt_msg.timeout(this_turn, next_turn)
                    return 'timeout', None
                timeout = True
                await self._prompt_msg.hurry(this_turn)
                continue


class ReversiSquare(BaseSquare):
    pass


class ReversiBoard(BaseBoard):
    def __init__(self) -> None:
        super().__init__('🌑', '⚪', '🟩', 8, ReversiSquare)
        self.rows = [
            [self._all_squares[self.length * y + x] for x in range(8)] for y in range(8)
        ]  # columns work with [x][y] access here too, instead of rows
        self.columns = [[r[n] for r in self.rows] for n in range(8)]
        self.columns[3][4].occupier = '2'
        self.columns[4][3].occupier = '2'
        self.columns[3][3].occupier = '1'
        self.columns[4][4].occupier = '1'
        self.right_diagonals: list[list[ReversiSquare]] = [
            [(0, 5)],
            [(0, 4)],
            [(0, 3)],
            [(0, 2)],
            [(0, 1)],
            [(0, 0)],
            [(1, 0)],
            [(2, 0)],
            [(3, 0)],
            [(4, 0)],
            [(5, 0)],
        ]
        self.left_diagonals: list[list[ReversiSquare]] = [
            [(0, 2)],
            [(0, 3)],
            [(0, 4)],
            [(0, 5)],
            [(0, 6)],
            [(0, 7)],
            [(1, 7)],
            [(2, 7)],
            [(3, 7)],
            [(4, 7)],
            [(5, 7)],
        ]
        for n in range(1, 8):
            for right_list in self.right_diagonals:
                try:
                    right_list.append(
                        self.columns[right_list[0][0] + n][right_list[0][1] + n]
                    )
                except IndexError:
                    continue
            for left_list in self.left_diagonals:
                try:
                    if left_list[0][1] - n < 0:
                        continue
                    left_list.append(
                        self.columns[left_list[0][0] + n][left_list[0][1] - n]
                    )
                except IndexError:
                    continue
        for lst in self.right_diagonals:
            lst[0] = self.columns[lst[0][0]][lst[0][1]]
        for lst in self.left_diagonals:
            lst[0] = self.columns[lst[0][0]][lst[0][1]]

    async def to_emojis(self) -> str:
        string_list = str(self).splitlines(keepends=True)

        for k, string in enumerate(string_list.copy()):
            string_list[k] = (
                NUM_EMOTES[:8][-k - 1]
                + ' '
                + string.replace('1', ':new_moon:')
                .replace('2', ':white_circle:')
                .replace('0', ':green_square:')
            )
        part1 = ''.join(string_list[0:3])
        part2 = ''.join(string_list[3:6])
        part3 = ''.join(string_list[6:])
        return (part1, part2, part3 + '\n🟦 ' + ''.join(NUM_EMOTES[0:8]))

    async def is_valid_square(self, x: int, y: int, value: str) -> bool:
        square = self._all_squares[self.length * y - self.length + x - 1]
        if square.occupier != '0':
            return False
        square.occupier = value
        rdiag, ldiag = [], []
        for diag in self.right_diagonals:
            if square in diag:
                rdiag = diag
        for diag in self.left_diagonals:
            if square in diag:
                ldiag = diag

        has_square, spans = [], []
        if span := await self._find_across(self.columns[x - 1], value):
            has_square.append(self.columns[x - 1])
            spans.append(span)
        if span := await self._find_across(self.rows[y - 1], value):
            has_square.append(self.rows[y - 1])
            spans.append(span)
        if span := await self._find_across(rdiag, value):
            has_square.append(rdiag)
            spans.append(span)
        if span := await self._find_across(ldiag, value):
            has_square.append(ldiag)
            spans.append(span)
        if not has_square:
            square.occupier = '0'
            return False
        for k, lst in enumerate(has_square):
            for sq in lst[spans[k][0] + 1 : spans[k][1] - 1]:
                sq.occupier = value
        return True

    async def set_square(self, x: int, y: int, value: Literal['1', '2']) -> None:
        return None

    @staticmethod
    async def _find_across(lst: list, char: str) -> tuple:
        string = ''.join([square.occupier for square in lst])
        try:
            if char == '1':
                return re.search(r'1[12]*2[12]*1', string).span()
            else:
                return re.search(r'2[12]*1[12]*2', string).span()
        except AttributeError:
            return ()

    async def check_win(self) -> tuple[int, int]:
        white = 0
        black = 0
        for square in self._all_squares:
            if square.occupier == '1':
                black += 1
            elif square.occupier == '2':
                white += 1
        return black, white


class ReversiGame(BaseGame):
    def __init__(
        self,
        ctx: commands.Context,
        bot: commands.Bot,
        opponent: discord.Member,
        time: int = 10,
    ) -> None:
        super().__init__(
            ctx,
            bot,
            opponent,
            ReversiBoard,
            'Black',
            'White',
            C.BOLD_GRAY_H_INDIGO,
            C.BOLD_WHITE_H_INDIGO,
            64,
            r'(?P<x>[1-8])[, ]*(?P<y>[1-8])',
            45,
        )
        self._input_occupied_error = 'invalid'

        self._time = time
        self._start_time = None

    async def _loop_begin(self) -> bool:
        self._start_time = datetime.datetime.now()
        await self._ctx.send(
            f'{C.B}{C.BOLD_GREEN}Time limit: {C.CYAN}{self._time} minutes!\n'
            f'{self._player1.color}{self._player1.symbol}: {self._player1}, '
            f'{self._player2.color}{self._player2.symbol}: {self._player2}{C.E}'
        )
        boart1, board2, board3 = await self._board.to_emojis()
        msg1 = await self._ctx.send(boart1)
        msg2 = await self._ctx.send(board2)
        msg3 = await self._ctx.send(board3)
        self._board_msg = BoardMessage([msg1, msg2, msg3], self._board)
        self._prompt_msg = PromptMessage(
            await self._ctx.send(
                f"{self._player1.mention} {self._player1.symbol}'s turn!"
            )
        )
        return False

    async def _iter_begin(self, this_turn: Player, next_turn: Player) -> bool:
        delta: datetime.timedelta = datetime.datetime.now() - self._start_time
        if delta.seconds / 60 > self._time:
            await self._check_board_win(
                this_turn, next_turn, force=True, time_is_out=True
            )
            return True

        await self._prompt_msg.update(this_turn)

    async def _loop_end(self, this_turn: Player, next_turn: Player) -> None:
        await self._check_board_win(this_turn, next_turn)

    async def _check_board_win(
        self,
        this_turn: Player,
        next_turn: Player,
        *,
        force: bool = False,
        time_is_out: bool = False,
    ) -> bool:
        if not force:
            return False

        black, white = await self._board.check_win()
        if black == white:
            await self._prompt_msg.winner(
                this_turn,
                points_ratio=(black, white),
                draw=True,
                time_is_out=time_is_out,
            )
            self.winner = this_turn.member
            self.loser = next_turn.member
            self.tie = True
        elif black > white:
            await self._prompt_msg.winner(
                self._player1, points_ratio=(black, white), time_is_out=time_is_out
            )
            self.winner = self._player1.member
            self.loser = self._player2.member
        else:
            await self._prompt_msg.winner(
                self._player2, points_ratio=(white, black), time_is_out=time_is_out
            )
            self.winner = self._player2.member
            self.loser = self._player1.member
        return True


class WeiqiSquare(BaseSquare):
    def __init__(self, x: int, y: int) -> None:
        super().__init__()
        self.x = x
        self.y = y
        self.up = None
        self.down = None
        self.right = None
        self.left = None

    @property
    def neighbors(self) -> list[WeiqiSquare]:
        return [
            sq for sq in [self.up, self.down, self.right, self.left] if sq is not None
        ]

    async def liberty(self) -> tuple[bool, list[WeiqiSquare]]:
        """checks this square's liberty

        returns a list of [liberty: bool, group: set[Square]]. liberty is if
        the group has liberty. group is a set of all squares of the connected group.
        """
        group = {self}
        return await self._liberty2(group), group

    async def _liberty2(self, group: set) -> bool:
        # modifies gp
        print('lib2')
        if self.occupier == '0':
            return True
        for square in self.neighbors:
            if square.occupier == '0':
                return True
        for square in self.neighbors:
            if square.occupier == self.occupier and square not in group:
                group.add(square)
                if await square._liberty2(group):
                    return True
        return False

    async def empty_group(self) -> tuple[Literal['0', '1', '2'], set[WeiqiSquare]]:
        """gets a set of all neighboring squares if its occ is 0"""
        print('call')
        emptygroup = {self}
        surrounded = set(self.neighbors)
        await self._group2(emptygroup, surrounded)
        bcount = wcount = 0
        for sq in surrounded.copy():
            if sq.occupier == '1':
                bcount += 1
            elif sq.occupier == '2':
                wcount += 1
        if bcount and wcount:
            return '0', emptygroup
        if bcount:
            return '1', emptygroup
        if wcount:
            return '2', emptygroup
        return '0', emptygroup

    async def _group2(self, gp: set, sr: set) -> bool:
        # modifies gp and sr
        for sq in self.neighbors:
            if sq.occupier == '0' and sq not in gp:
                gp |= {sq}
                sr |= set(sq.neighbors)
                await sq._group2(gp, sr)


class WeiqiBoard(BaseBoard):
    def __init__(self) -> None:
        self.p1_emoji = '🌑'
        self.p2_emoji = '⚪'
        self.no_emoji = '🟫'
        self.length = 19
        self.square_type = WeiqiSquare

        self._unliberated = set()
        self._numof_unlib = 0
        self._b_prisoners = 0
        self._w_prisoners = 0

        self._rows = [
            [self.square_type(x, y) for x in range(self.length)]
            for y in range(self.length)
        ]
        self._columns = [[r[n] for r in self._rows] for n in range(self.length)]
        for k, rw in enumerate(self._rows):
            if k != 0:
                for n in range(self.length):
                    rw[n].down = self._rows[k - 1][n]
            if k != self.length - 1:
                for n in range(self.length):
                    rw[n].up = self._rows[k + 1][n]
        for k, cl in enumerate(self._columns):
            if k != 0:
                for n in range(self.length):
                    cl[n].left = self._columns[k - 1][n]
            if k != self.length - 1:
                for n in range(self.length):
                    cl[n].right = self._columns[k + 1][n]

    def __str__(self) -> str:
        raise TypeError

    async def to_emojis(self) -> list[discord.Embed]:
        NUMS = '⒈⒉⒊⒋⒌⒍⒎⒏⒐⒑⒒⒓⒔⒕⒖⒗⒘⒙⒚'
        final_string = ''
        for k, row in enumerate(self._rows):
            as_string = ''.join([square.occupier for square in row])
            final_string = ''.join([f'{NUMS[k]:>3} {as_string:>3}\n', final_string])
        final_string = (
            final_string.replace('1', self.p1_emoji)
            .replace('2', self.p2_emoji)
            .replace('0', self.no_emoji)
        )
        return [
            discord.Embed(
                description=f'```{final_string}'
                f'{"     ⒈ ⒉ ⒊ ⒋⒌ ⒍⒎ ⒏ ⒐⒑ ⒒ ⒓ ⒔⒕ ⒖ ⒗ ⒘⒙ ⒚"}```'
            )
        ]

    async def is_valid_square(self, x: int, y: int, value: str) -> bool:
        x -= 1
        y -= 1
        square = self._columns[x][y]
        if square.occupier != '0' or square in self._unliberated:
            return False
        return True

    async def set_square(self, x: int, y: int, value: Literal['1', '2']) -> None:
        self._columns[x - 1][y - 1].occupier = value
        await self._all_liberties()

    async def _all_liberties(self):
        checked: set[WeiqiSquare] = set()
        to_die: set[WeiqiSquare] = set()
        if self._numof_unlib == 3:
            self._unliberated.clear()
            self._numof_unlib = 0
        for column in self._columns:
            for square in column:
                if square in checked:
                    continue
                has_liberty, group = await square.liberty()
                checked |= group
                if not has_liberty:
                    self._unliberated |= group
                    to_die |= group
        for s in to_die:
            if s.occupier == '1':
                self._w_prisoners += 1
            else:
                self._b_prisoners += 1
            s.occupier = '0'
        self._numof_unlib += 1

    async def _all_emptygroups(self) -> tuple[int, int]:
        print('all empty call')
        checked = set()
        black_captured_groups = 0
        white_captured_groups = 0
        for column in self._columns:
            for square in column:
                if square.occupier != '0' or square in checked:
                    continue
                surround, group = await square.empty_group()
                checked |= group
                if surround == '1':
                    black_captured_groups += len(group)
                    for sq in group:
                        sq.occupier = '⬛'
                elif surround == '2':
                    white_captured_groups += len(group)
                    for sq in group:
                        sq.occupier = '⬜'
        print(black_captured_groups, white_captured_groups)
        return black_captured_groups, white_captured_groups

    async def check_win(self) -> tuple[int, ...]:
        b_num = w_num = 0
        for column in self._columns:
            for square in column:
                if square.occupier == '1':
                    b_num += 1
                elif square.occupier == '2':
                    w_num += 1
        b_captured, w_captured = await self._all_emptygroups()
        print(b_num, b_captured, '\n', w_num, w_captured)
        return (
            b_num + b_captured + self._b_prisoners,
            w_num + w_captured + self._w_prisoners,
        )


class WeiqiGame(BaseGame):
    def __init__(
        self,
        ctx: commands.Context,
        bot: commands.Bot,
        opponent: discord.Member,
        time: int = 20,
    ) -> None:
        super().__init__(
            ctx,
            bot,
            opponent,
            WeiqiBoard,
            'Black',
            'White',
            C.BOLD_GRAY_H_INDIGO,
            C.BOLD_WHITE_H_INDIGO,
            500,
            r'(?P<x>1[0-9]|[1-9])[, ]*(?P<y>1[0-9]|[1-9])',
            45,
        )

        self._time = time
        self._start_time = None

    async def _loop_begin(self) -> bool:
        self._start_time = datetime.datetime.now()
        await self._ctx.send(
            f'{C.B}{C.BOLD_GREEN}Time limit: {C.CYAN}{self._time} minutes!\n'
            f'{self._player1.color}{self._player1.symbol}: {self._player1}, '
            f'{self._player2.color}{self._player2.symbol}: {self._player2}{C.E}'
        )
        self._board_msg = BoardMessage(
            await self._ctx.send(embeds=await self._board.to_emojis()), self._board
        )
        self._prompt_msg = PromptMessage(
            await self._ctx.send(
                f"{self._player1.mention} {self._player1.symbol}'s turn!"
            )
        )
        return False

    async def _iter_begin(self, this_turn: Player, next_turn: Player) -> bool:
        delta: datetime.timedelta = datetime.datetime.now() - self._start_time
        if delta.seconds / 60 > self._time:
            await self._check_board_win(
                this_turn, next_turn, force=True, time_is_out=True
            )
            return True

        await self._prompt_msg.update(this_turn)

    async def _check_board_win(
        self,
        this_turn: Player,
        next_turn: Player,
        *,
        force: bool = False,
        time_is_out: bool = False,
    ) -> bool:
        if not force:
            return False

        black, white = await self._board.check_win()
        await self._board_msg.update()
        if black == white:
            await self._prompt_msg.winner(
                this_turn,
                points_ratio=(black, white),
                draw=True,
                time_is_out=time_is_out,
            )
            self.winner = this_turn.member
            self.loser = next_turn.member
            self.tie = True
        elif black > white:
            await self._prompt_msg.winner(
                self._player1, points_ratio=(black, white), time_is_out=time_is_out
            )
            self.winner = self._player1.member
            self.loser = self._player2.member
        else:
            await self._prompt_msg.winner(
                self._player2, points_ratio=(white, black), time_is_out=time_is_out
            )
            self.winner = self._player2.member
            self.loser = self._player1.member
        return True


class BattleshipSquare(BaseSquare):
    pass


class BattleshipBoard(BaseBoard):
    def __init__(self, player: Player) -> None:
        super().__init__('⬜', '\U0001f7e9', '🟦', 10, BattleshipSquare)
        self.player = player
        self.hit_ship = False
        self.sank_ship = False

        self.rows = [
            [self._all_squares[self.length * y + x] for x in range(10)]
            for y in range(10)
        ]
        self.columns = [[r[n] for r in self.rows] for n in range(10)]

        self.old_ships: list[BattleshipSquare] = []
        self.ships = [
            AllPoints(coords)
            for coords in (
                ((5, 3), (5, 4), (5, 5), (5, 6), (5, 7)),
                ((5, 4), (5, 5), (5, 6), (5, 7)),
                ((5, 4), (5, 5), (5, 6)),
                ((5, 4), (5, 5), (5, 6)),
                ((5, 5), (5, 6)),
            )
        ]

    async def to_emojis(self) -> str:
        string = (
            str(self)
            .replace('1', self.p1_emoji)
            .replace('2', self.p2_emoji)
            .replace('0', self.no_emoji)
        )
        waves_string = ''
        reversed_nums = tuple(reversed(NUM_EMOTES))
        for k, char in enumerate(string):
            if k % 11 == 0:
                waves_string += reversed_nums[int(k / 10)] + ' '
            if char == self.no_emoji and not randint(0, 4):
                waves_string += '🌊'
                continue
            waves_string += char
        waves_string += '\n🟦 ' + ''.join(NUM_EMOTES)
        return waves_string

    async def get_square(self, x: int, y: int) -> BattleshipSquare:
        """getter only for use with old_squares"""
        return self._all_squares[self.length * int(y) - self.length + int(x) - 1]

    async def initial_set_square(self, x: int, y: int, value: Literal['1', '2']):
        self._all_squares[
            self.length * int(y) - self.length + int(x) - 1
        ].occupier = value

    async def set_square(self, x: int, y: int, value: Literal['1', '2']) -> None:
        x, y = int(x), int(y)
        self.hit_ship = False
        self.sank_ship = False
        set_square = self._all_squares[self.length * y - self.length + x - 1]
        set_square.occupier = '📌'
        if set_square in self.old_ships:
            print('reached never')
            set_square.occupier = '💥'
            self.hit_ship = True
        for k, ship in enumerate(self.ships):
            this_squares: list[BattleshipSquare] = [
                self._all_squares[self.length * y - self.length + x - 1]
                for x, y in [(int(point.x), int(point.y)) for point in ship.allpoints]
            ]
            if all([square.occupier == '💥' for square in this_squares]):
                self.ships.pop(k)
                self.sank_ship = True
                for sq in this_squares:
                    sq.occupier = '🔥'
                break

    async def check_win(self) -> int:
        remaining = 0
        for ship in self.ships:
            remaining += len(ship.allpoints)
        print('bd return remaining', remaining)
        return remaining

    async def reveal_ships(self) -> None:
        for square in self.old_ships:
            if square.occupier == '0':
                square.occupier = '1'


class DirectionsButtonView(ui.View):
    SHIP_NAMES = ('Carrier', 'Battleship', 'Cruiser', 'Submarine', 'Destroyer')

    def __init__(
        self, superview: EmphemeralBattleshipStartView, board: BattleshipBoard
    ):
        super().__init__(timeout=20)
        self.board = board
        self.superview = superview

        self._current_ship = 0

        for k, value in zip(
            (0, 0, 0, 1, 1, 1),
            (
                '\U0001f501',
                '\U0001f53c',
                '\U0001f197',
                '\U000025c0\U0000fe0f',
                '\U0001f53d',
                '\U000025b6\U0000fe0f',
            ),
        ):
            self.add_item(DirectionButton(k, value))

    async def wait(self) -> bool:
        res = await super().wait()
        if res:
            if self.board.player.member.id == self.superview.player1.member.id:
                raise asyncio.TimeoutError
            raise TimeoutError
        return res

    async def handle_button_interaction(
        self, interaction: discord.Interaction, button: DirectionButton
    ):
        Point = namedtuple('Point', ['x', 'y'])
        move_point = None
        rotate = None
        match button.direction:
            case 'up':
                move_point = Point(0, 1)
            case 'down':
                move_point = Point(0, -1)
            case 'left':
                move_point = Point(-1, 0)
            case 'right':
                move_point = Point(1, 0)
            case 'rotate':
                ship = self.board.ships[self._current_ship].allpoints
                center = ship[len(ship) // 2]
                rotate = (center, radians(90))
        if button.direction == 'ok':
            self.board.old_ships.extend(
                [
                    await self.board.get_square(point.x, point.y)
                    for point in self.board.ships[self._current_ship].allpoints
                ]
            )
            self._current_ship += 1
            for square in self.board.old_ships:
                square.occupier = '1'
            if self._current_ship == 5:
                self.clear_items()
                await interaction.response.edit_message(
                    content=f'{C.B}{C.BLUE}All done! Now just wait for your opponent.{C.E}',
                    embed=discord.Embed(description=await self.board.to_emojis()),
                    view=self,
                )
                self.stop()
            else:
                await self.board_add()
                await self.check_button_usable()
                await interaction.response.edit_message(
                    content=f'{C.B}{C.BOLD_GRAY_H_INDIGO}{self.__class__.SHIP_NAMES[self._current_ship]}{C.E}',
                    embed=discord.Embed(description=await self.board.to_emojis()),
                    view=self,
                )
        else:
            await self.board_remove()
            for square in self.board.old_ships:
                square.occupier = '1'
            if move_point:
                self.board.ships[self._current_ship].translate_all(move_point)
            elif rotate:
                self.board.ships[self._current_ship].rotate_all(rotate)
            await self.board_add()
            await self.check_button_usable()
            await interaction.response.edit_message(
                embed=discord.Embed(description=await self.board.to_emojis()), view=self
            )

    async def board_add(self):
        for x, y in [
            (point.x, point.y)
            for point in self.board.ships[self._current_ship].allpoints
        ]:
            await self.board.initial_set_square(x, y, '2')

    async def board_remove(self):
        for x, y in [
            (point.x, point.y)
            for point in self.board.ships[self._current_ship].allpoints
        ]:
            await self.board.initial_set_square(x, y, '0')

    async def check_button_usable(self) -> None:
        this_ship = [
            await self.board.get_square(point.x, point.y)
            for point in self.board.ships[self._current_ship].allpoints
        ]
        for square in self.board.old_ships:
            if square in this_ship:
                self.children[2].disabled = True
                break
        else:
            self.children[2].disabled = False

        edges = [
            self.board.columns[0],
            self.board.columns[-1],
            self.board.rows[0],
            self.board.rows[-1],
        ]
        if self._current_ship < 2:
            edges.extend(
                [
                    self.board.columns[1],
                    self.board.columns[-2],
                    self.board.rows[1],
                    self.board.rows[-2],
                ]
            )
        for edge in edges:
            if all([point in edge for point in this_ship]):
                self.children[0].disabled = True
                break
        else:
            self.children[0].disabled = False

        for k, edge in zip(
            (1, 3, 4, 5),
            (
                self.board.rows[-1],
                self.board.columns[0],
                self.board.rows[0],
                self.board.columns[-1],
            ),
        ):
            if any([point in edge for point in this_ship]):
                self.children[k].disabled = True
            else:
                self.children[k].disabled = False


class DirectionButton(ui.Button):
    DIRECTIONS = {
        '\U0001f501': 'rotate',
        '\U0001f53c': 'up',
        '\U0001f197': 'ok',
        '\U000025c0\U0000fe0f': 'left',
        '\U0001f53d': 'down',
        '\U000025b6\U0000fe0f': 'right',
    }

    def __init__(self, row: int, emote: str):
        super().__init__(style=discord.ButtonStyle.primary, emoji=emote, row=row)
        self.direction = self.__class__.DIRECTIONS[emote]

    async def callback(self, interaction: discord.Interaction):
        await self.view.handle_button_interaction(interaction, self)


class EmphemeralBattleshipStartView(ui.View):
    def __init__(self, bot: commands.Bot, p1: Player, p2: Player):
        super().__init__(timeout=20)
        self.bot = bot
        self.player1 = p1
        self.player2 = p2
        self.message: discord.Message = None

        self.subview1: DirectionsButtonView = None
        self.subview2: DirectionsButtonView = None
        self.interaction1: discord.Interaction = None
        self.interaction2: discord.Interaction = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.player1.member.id, self.player2.member.id):
            await interaction.response.send_message(
                f'{C.B}{C.RED}You are not playing.{C.E}', ephemeral=True
            )
            return False
        if (interaction.user.id == self.player1.member.id and self.subview1) or (
            interaction.user.id == self.player2.member.id and self.subview2
        ):
            await interaction.response.send_message(
                f'{C.B}{C.RED}You already have started.{C.E}', ephemeral=True
            )
            return False
        return True

    @ui.button(label='start')
    async def press(self, interaction: discord.Interaction, button: ui.Button):
        this_board = BattleshipBoard(Player(interaction.user))
        for x, y in [(point.x, point.y) for point in this_board.ships[0].allpoints]:
            await this_board.initial_set_square(x, y, '2')
        buttons_view = DirectionsButtonView(self, this_board)
        if interaction.user.id == self.player1.member.id:
            self.subview1 = buttons_view
            self.interaction1 = interaction
            if self.subview2:
                self.children[0].disabled = True
                self.message = await self.message.edit(view=self)
        else:
            self.subview2 = buttons_view
            self.interaction2 = interaction
            if self.subview1:
                self.children[0].disabled = True
                self.message = await self.message.edit(view=self)
        await interaction.response.send_message(
            f'{C.B}{C.BLUE}Lay out your ships! - {C.BOLD_GRAY_H_INDIGO}Carrier{C.E}',
            embed=discord.Embed(description=await this_board.to_emojis()),
            view=buttons_view,
            ephemeral=True,
        )


class SingleBattleshipBoardAdapter(BaseBoard):
    def __init__(self, b1: BattleshipBoard, b2: BattleshipBoard) -> None:
        self._board1 = b1
        self._board2 = b2
        self.this_turn = '1'
        self.hit = False
        self.sank = False

    async def set_square(self, x: int, y: int, value: Literal['1', '2']) -> None:
        if value == '1':
            await self._board2.set_square(x, y, value)
            self.hit, self.sank = self._board2.hit_ship, self._board2.sank_ship
        else:
            await self._board1.set_square(x, y, value)
            self.hit, self.sank = self._board1.hit_ship, self._board1.sank_ship

    async def is_valid_square(self, x: int, y: int, value: str) -> bool:
        if value == '1':
            return await self._board2.is_valid_square(x, y, value)
        return await self._board1.is_valid_square(x, y, value)

    async def to_emojis(self) -> list[discord.Embed]:
        if self.this_turn == '1':
            title = "Blue's Ocean"
            desc = await self._board2.to_emojis()
            color_hex = (51, 153, 255)
        else:
            title = "Red's Ocean"
            desc = await self._board1.to_emojis()
            color_hex = (255, 0, 0)
        return [
            discord.Embed(
                title=title,
                description=desc,
                colour=discord.Colour.from_rgb(*color_hex),
            )
        ]

    async def check_win(self) -> tuple[int, int]:
        return await self._board1.check_win(), await self._board2.check_win()

    async def reveal_ships(self) -> list[discord.Embed]:
        return [
            discord.Embed(description=await self._board1.reveal_ships()),
            discord.Embed(description=await self._board2.reveal_ships()),
        ]


class BattleshipGame(BaseGame):
    def __init__(
        self, ctx: commands.Context, bot: commands.Bot, opponent: discord.Member
    ) -> None:
        super().__init__(
            ctx,
            bot,
            opponent,
            object,
            'Red',
            'Blue',
            C.RED,
            C.BLUE,
            200,
            r'(?P<x>[1-9]0??)[, ]*(?P<y>[1-9]0??)',
            45,
        )

    async def _loop_begin(self) -> bool:
        start_view = EmphemeralBattleshipStartView(
            self._bot, self._player1, self._player2
        )
        start_message = await self._ctx.send(
            f'{C.B}{C.BOLD_RED}Red: {C.RED}{self._player1}{C.YELLOW}, '
            f'{C.BOLD_BLUE}Blue: {C.BLUE}{self._player2}{C.E}',
            view=start_view,
        )
        start_view.message = start_message
        await start_view.wait()
        start_view.children[0].disabled = True
        view1, view2 = start_view.subview1, start_view.subview2
        if not view1 or not view2:
            errmsg = await self.cancel_messages(start_view, view1, view2)
            start_message = await start_message.edit(content=errmsg, view=start_view)
            return True

        board1, board2 = start_view.subview1.board, start_view.subview2.board
        task = asyncio.gather(view1.wait(), view2.wait())
        try:
            await task
        except asyncio.TimeoutError:
            cancel_info = (
                start_view.interaction2,
                view2,
                start_view.interaction1,
                view1,
                self._player1,
            )
        except TimeoutError:
            cancel_info = (
                start_view.interaction1,
                view1,
                start_view.interaction2,
                view2,
                self._player2,
            )
        else:
            start_message = await start_message.edit(view=start_view)
            self._board = SingleBattleshipBoardAdapter(board1, board2)
            for sq_list in board1.ships:
                for sq in sq_list.allpoints:
                    await board1.initial_set_square(sq.x, sq.y, '0')
            for sq_list in board2.ships:
                for sq in sq_list.allpoints:
                    await board2.initial_set_square(sq.x, sq.y, '0')
            self._board_msg = BoardMessage(
                await self._ctx.send(embeds=await self._board.to_emojis()), self._board
            )
            self._prompt_msg = PromptMessage(
                await self._ctx.send(
                    f"{self._player1.mention} {self._player1.symbol}'s turn! (send coordinates)"
                )
            )
            return False

        task.cancel()
        await self.cancel_view(view1)
        await self.cancel_view(view2)
        await cancel_info[0].edit_original_message(
            content=f'{C.B}{C.RED}Your opponent timed out.{C.E}', view=cancel_info[1]
        )
        await cancel_info[2].edit_original_message(
            content=f'{C.B}{C.RED}You timed out.{C.E}', view=cancel_info[3]
        )
        start_message = await start_message.edit(
            content=f'{C.B}{C.RED}{cancel_info[4]} timed out.{C.E}', view=start_view
        )
        return True

    async def _iter_begin(self, this_turn: Player, next_turn: Player) -> bool:
        self._board.this_turn = this_turn.number
        await self._board_msg.update()
        await super()._iter_begin(this_turn, next_turn)

    async def _iter_end(self, this_turn: Player, next_turn: Player) -> bool:
        if self._flush:
            self._flush = False
            await self._flush_channel()
        await self._board_msg.update()
        self._board: SingleBattleshipBoardAdapter
        if self._board.sank:
            await self._ctx.send(
                f'{C.B}{C.GREEN}Hit! and a ship has sunken!{C.E}', delete_after=2
            )
            await asyncio.sleep(2)
        elif self._board.hit:
            await self._ctx.send(f'{C.B}{C.GREEN}Hit!{C.E}', delete_after=2)
            await asyncio.sleep(2)
        else:
            await self._ctx.send(f'{C.B}{C.RED}Miss!{C.E}', delete_after=2)
            await asyncio.sleep(2)

        if await self._check_board_win(this_turn, next_turn):
            await self._board_msg.message.edit(embeds=await self._board.reveal_ships())
            return True
        return False

    async def _timeout(self, this_turn: Player, next_turn: Player) -> None:
        await self._board_msg.message.edit(embeds=await self._board.reveal_ships())
        await super()._timeout(this_turn, next_turn)

    async def _end(self, this_turn: Player, next_turn: Player) -> None:
        await self._board_msg.message.edit(embeds=await self._board.reveal_ships())
        await super()._end(this_turn, next_turn)

    async def _check_board_win(
        self, this_turn: Player, next_turn: Player, *, force: bool = False
    ) -> bool:
        red, blue = await self._board.check_win()
        print('checking', red, blue)
        if blue == 0:
            await self.red_winner((17 - red, 17 - blue))
            return True
        if red == 0:
            await self.blue_winner((17 - blue, 17 - red))
            return True
        if force:
            if red > blue:
                await self.red_winner((17 - red, 17 - blue))
                return True
            if blue > red:
                await self.blue_winner((17 - blue, 17 - red))
                return True
            self.winner = this_turn.member
            self.loser = next_turn.member
            self.tie = True
            await self._prompt_msg.draw()
            return True
        print('check false')
        return False

    async def red_winner(self, ratio: tuple[int, int]) -> None:
        print('red winner call')
        self.winner = self._player1.member
        self.loser = self._player2.member
        await self._prompt_msg.winner(self._player1, points_ratio=ratio)

    async def blue_winner(self, ratio: tuple[int, int]) -> None:
        print('blue winner call')
        self.winner = self._player2.member
        self.loser = self._player1.member
        await self._prompt_msg.winner(self._player2, points_ratio=ratio)

    @staticmethod
    async def cancel_view(view: ui.View):
        for child in view.children:
            child.disabled = True
        view.stop()

    async def cancel_messages(self, start_view, view1, view2) -> str:
        if not view1 and not view2:
            errmsg = f'{C.B}{C.RED}Timed out.{C.E}'
        elif not view1:
            await self.cancel_view(view2)
            start_view.interaction2 = (
                await start_view.interaction2.edit_original_message(
                    content=f'{C.B}{C.RED}Your opponent timed out.{C.E}', view=view2
                )
            )
            errmsg = f'{C.B}{C.RED}{self._player1} timed out.{C.E}'
        else:
            await self.cancel_view(view1)
            start_view.interaction1 = (
                await start_view.interaction1.edit_original_message(
                    content=f'{C.B}{C.RED}Your opponent timed out.{C.E}', view=view1
                )
            )
            errmsg = f'{C.B}{C.RED}{self._player2} timed out.{C.E}'
        return errmsg


class GameFeatures(commands.GroupCog, name='play'):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ingame: list[discord.Member] = []
        super().__init__()

    @commands.command(name='ingames')
    @commands.cooldown(rate=1, per=300, type=commands.BucketType.guild)
    @commands.guild_only()
    async def ingames(self, ctx: commands.Context, clear: bool = False):
        await ctx.send(f'```py\n{[member.display_name for member in self.ingame]}```')
        if clear:
            self.ingame = []
            await ctx.send(f'{C.B}{C.GREEN}cleared!{C.E}')

    @app_commands.command(name='tic-tac-toe')
    async def tictactoe(self, ctx: commands.Context, opponent: discord.Member):
        if await self.wait_confirm(ctx, opponent, 'Tic-Tac-Toe'):
            return
        game = TicTacToeGame(ctx, self.bot, opponent)
        await game.start()
        await self.done_playing('tictactoe', game.winner, game.loser, game.tie)

    @app_commands.command(name='connect-four')
    async def connectfour(self, ctx: commands.Context, opponent: discord.Member):
        if await self.wait_confirm(ctx, opponent, 'Connect-Four'):
            return
        game = ConnectFourGame(ctx, self.bot, opponent)
        await game.start()
        await self.done_playing('connectfour', game.winner, game.loser, game.tie)

    @app_commands.command(name='reversi')
    async def reversi(self, ctx: commands.Context, opponent: discord.Member):
        if await self.wait_confirm(ctx, opponent, 'Reversi'):
            return
        game = ReversiGame(ctx, self.bot, opponent)
        await game.start()
        await self.done_playing('reversi', game.winner, game.loser, game.tie)

    @app_commands.command(name='weiqi')
    async def weiqi(self, ctx: commands.Context, opponent: discord.Member):
        if await self.wait_confirm(ctx, opponent, 'Weiqi'):
            return
        game = WeiqiGame(ctx, self.bot, opponent)
        await game.start()
        await self.done_playing('weiqi', game.winner, game.loser, game.tie)

    @app_commands.command(name='battleship')
    async def battleship(self, ctx: commands.Context, opponent: discord.Member):
        if await self.wait_confirm(ctx, opponent, 'Battleship'):
            return
        game = BattleshipGame(ctx, self.bot, opponent)
        await game.start()
        await self.done_playing('battleship', game.winner, game.loser, game.tie)

    async def wait_confirm(
        self, octx: commands.Context, opp: discord.guild.Member, game: str
    ) -> int:
        """wait for confirmation that the opp wants to play game"""
        if octx.author in self.ingame:
            await octx.send(f'{C.B}{C.RED}you are already in another game.{C.E}')
            return 1

        if opp in self.ingame:
            await octx.send(
                f'{C.B}{C.RED}{opp.display_name} is already in another game. '
                f'wait for it to finish or try another person!{C.E}'
            )
            return 1

        if opp == octx.author:
            await octx.send(f'{C.B}{C.RED}you cannot challenge yourself.{C.E}')
            return 1

        if opp == self.bot.user:
            await octx.send(f'{C.B}{C.RED}no.{C.E}')
            return 1

        self.ingame.append(octx.author)
        inv = await octx.send(
            f'{octx.message.author.display_name} has challenged {opp.display_name} '
            f'to a match of {game.title()}! {opp.mention}, do you accept? '
            '(react with :white_check_mark: or :negative_squared_cross_mark:)'
        )
        await inv.add_reaction('✅')
        await inv.add_reaction('❎')

        def chk(r, u):
            return u == opp and str(r.emoji) in '✅❎'

        reaction = ''
        status = ''
        try:
            reaction, user = await self.bot.wait_for(
                'reaction_add', check=chk, timeout=30
            )
        except asyncio.TimeoutError:
            await octx.send(
                f'{C.B}{C.RED}command timed out. it seems that {opp.display_name} '
                f'does not want to play rn. try someone else!{C.E}'
            )
            self.ingame.remove(octx.author)
            status = 'ignored'
        if reaction:
            if str(reaction.emoji) == '❎':
                await inv.reply(f'{opp.display_name} did not accept the challenge.')
                self.ingame.remove(octx.author)
                status = 'rejected'
            elif str(reaction.emoji) == '✅':
                await inv.reply(f'{opp.display_name} has accepted the challenge!')
                self.ingame.append(opp)
                status = 'accepted'
        now = datetime.datetime.now().strftime("%m/%d, %H:%M:%S")

        if game == 'go':
            game = 'weiqi'
        elif game == 'othello':
            game = 'reversi'

        async with aopen(self.bot.files['game_log'], 'a') as gl:
            await gl.write(
                f'{now} | {octx.author.display_name}{game:>16} {opp.display_name:>17},{status:>18}\n'
            )
        if status in {'ignored', 'rejected'}:
            return 1
        return 0

    async def done_playing(
        self, game: str, p1: discord.Member, p2: discord.Member, tie=False
    ):
        self.ingame.remove(p1)
        self.ingame.remove(p2)
        await self.bot.database.set_games_winloss(p1.id, p2.id, game, tie)


async def setup(bot: commands.Bot):
    await bot.add_cog(GameFeatures(bot))
    print('LOADED games')
