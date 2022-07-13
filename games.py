from __future__ import annotations

import asyncio
import datetime
import re
from math import radians
from random import randint
from typing import TYPE_CHECKING, Any, Literal, NoReturn, Optional, cast

import discord
from aiofiles import open as aopen
from discord import ui
from discord.ext import commands

from extensions import ANSIColors as C
from extensions.definitions import NUM_EMOTES, owner_bypass
from extensions.transformations import AllPoints, Point

if TYPE_CHECKING:
    from vesuvius import Vesuvius


class BaseSquare:
    """Base class for a square on any board."""

    def __init__(self) -> None:
        self.occupier: Literal['1', '2', '0'] | str = '0'


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
        square_type: type[BaseSquare] = BaseSquare,
    ) -> None:
        """Initialize a board."""
        ...

    def __str__(self) -> str:
        ...

    async def to_emojis(
        self,
    ) -> str | tuple[str, ...] | discord.Embed | list[discord.Embed]:
        """Convert to discord emojis.

        This returns a string version of the board ready to be sent directly to discord.
        """
        ...

    async def is_valid_square(self, x: int, y: int, value: Literal['1', '2']) -> bool:
        """Check if a player can place a piece in x, y.

        x and y are not compared to the size of the board,
        this will raise IndexError if they are too big.

        By default this decides based on whether the spot is empty, but
        it can be overriden for special games.
        """
        ...

    async def set_square(self, x: int, y: int, value: Literal['1', '2']) -> None:
        """Set a square to a new value.

        This assumes that setting the square does not break any game rules,
        and that x and y are within the board range.
        """
        ...

    async def check_win(self) -> Literal['0', '1', '2'] | None | tuple[int, int]:
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
        self.message: discord.Message | list[discord.Message] = message
        self.board: BaseBoard = board

    async def update(self) -> None:
        await self.update_message(await self.board.to_emojis())

    async def update_message(
        self, new: str | tuple[str] | discord.Embed | list[discord.Embed]
    ):
        if isinstance(self.message, discord.Message):
            if isinstance(new, str):
                self.message = await self.message.edit(content=new)
                return
            elif isinstance(new, discord.Embed):
                self.message = await self.message.edit(embed=new)
                return
            elif isinstance(new, list):
                self.message = await self.message.edit(embeds=new)
                return
            raise TypeError

        self.message = cast(list[discord.Message], self.message)
        for k, v in enumerate(cast(tuple[str], new)):
            self.message[k] = await self.message[k].edit(content=v)
        return


class Player:
    """Represents a player."""

    def __init__(self, m: discord.Member) -> None:
        self.member = m
        self.mention = m.mention

        self.symbol: str = ''
        self.number: Literal['1', '2'] = '1'
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
        ctx: commands.Context[Vesuvius] | InteractionContextAdapter,
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
        ...

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
        ...

    async def _loop_begin(self) -> bool:
        """Called before the input loop starts.

        This method is responsble for sending information about which player is what color,
        sending the prompt message and setting `self._prompt_msg`, and sending the
        board message and setting `self._board_msg`

        If this method returns True, the game will exit.
        """
        ...
        return False

    async def _iter_begin(self, this_turn: Player, next_turn: Player) -> bool:
        """Called at the start of every iteration.

        This method is responsible for calling `update` on the prompt message.

        If this method returns True, the game will exit.
        """
        ...

    async def _iter_end(self, this_turn: Player, next_turn: Player) -> bool:
        """Called at the end of every iteration of the input loop, after a
        `BaseBoard.set_square` call.

        This method is responsible for calling `update` on the board message, win
        checking with `self._check_board_win`, and flushing the channel with
        `self._flush_channel` if `self._flush` is True.

        If the method returns True, the game will exit.
        """
        ...

    async def _timeout(self, this_turn: Player, next_turn: Player) -> None:
        """Called when this turn's player times out."""
        ...

    async def _end(self, this_turn: Player, next_turn: Player) -> None:
        """Called when an end request is accepted."""
        ...

    async def _loop_end(self, this_turn: Player, next_turn: Player) -> None:
        """Called when the input loop exits.

        By default this sets the attribute `tie` to True,
        override this for different behavior.
        """
        ...

    async def _check_board_win(
        self, this_turn: Player, next_turn: Player, *, force: bool = False
    ) -> bool:
        """Called after every move, and called with `force=True` during end requests.

        By default this sets the attribute `winner` to the player of the current turn,
        override this for different behavior.
        """
        ...

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
        ...


# subclasses ===========================================================================


class TicTacToeBoard(BaseBoard):
    def __init__(self) -> None:
        super().__init__(':x:', ':o:', ':question:', 3)

    async def check_win(self) -> Literal['0', '1']:
        anylst = [
            self._all_equal(ls)
            for ls in [self._all_squares[i : i + 3] for i in (0, 3, 6)]
        ]
        anylst.append(self._all_equal([self._all_squares[i] for i in (0, 4, 8)]))
        anylst.append(self._all_equal([self._all_squares[i] for i in (2, 4, 6)]))
        if any(anylst):
            return '1'
        return '0'

    @staticmethod
    def _all_equal(ls: list[BaseSquare]) -> bool:
        return (
            ls[0].occupier != '0' and ls[0].occupier == ls[1].occupier == ls[2].occupier
        )


class TicTacToeGame(BaseGame):
    def __init__(
        self,
        ctx: commands.Context[Vesuvius] | InteractionContextAdapter,
        bot: commands.Bot,
        opponent: discord.Member,
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


class ConnectFourBoard(BaseBoard):
    def __init__(self) -> None:
        self.p1_emoji = '🟡'
        self.p2_emoji = '🔴'
        self.no_emoji = '⚫'
        self.length = 7
        self.square_type = BaseSquare
        self._all_squares: list[BaseSquare] = [
            self.square_type() for _ in range(self.length * 6)
        ]

        BoardRow = list[list[BaseSquare]]
        self.rows: BoardRow = [self._all_squares[k - 7 : k] for k in range(7, 43, 7)]
        self.columns: BoardRow = [[row[n] for row in self.rows] for n in range(7)]
        self.right_diagonals: BoardRow = [[] for _ in range(6)]
        self.left_diagonals: BoardRow = [[] for _ in range(6)]

        r_diag_starts = ((0, 2), (0, 1), (0, 0), (1, 0), (2, 0), (3, 0))
        l_diag_starts = ((0, 3), (0, 4), (0, 5), (1, 5), (2, 5), (3, 5))
        for n in range(7):
            for k, right_list in enumerate(self.right_diagonals):
                try:
                    right_list.append(
                        self.columns[r_diag_starts[k][0] + n][r_diag_starts[k][1] + n]
                    )
                except IndexError:
                    continue
            for k, left_list in enumerate(self.left_diagonals):
                try:
                    left_list.append(
                        self.columns[l_diag_starts[k][0] + n][l_diag_starts[k][1] - n]
                    )
                except IndexError:
                    continue

    async def to_emojis(self) -> tuple[str, str]:
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

    async def check_win(self) -> Literal['0', '1']:
        for lst in (self.rows, self.columns, self.right_diagonals, self.left_diagonals):
            for some_row in [
                ''.join(sl) for sl in [[p.occupier for p in l] for l in lst]
            ]:
                if some_row.find('1111') != -1:
                    return '1'
                if some_row.find('2222') != -1:
                    return '1'
        return '0'


class ConnectFourGame(BaseGame):
    def __init__(
        self,
        ctx: commands.Context[Vesuvius] | InteractionContextAdapter,
        bot: commands.Bot,
        opponent: discord.Member,
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
            '',
            30,
        )

    async def _loop_begin(self) -> bool:
        await self._ctx.send(
            f'{C.B}{self._player1.color}{self._player1.symbol}: {self._player1}, '
            f'{self._player2.color}{self._player2.symbol}: {self._player2}{C.E}'
        )
        as_emojis = await self._board.to_emojis()
        assert isinstance(as_emojis, tuple)
        board1, board2 = as_emojis

        msg1 = await self._ctx.send(board1)
        msg2 = await self._ctx.send(board2)
        self._board_msg = BoardMessage([msg1, msg2], self._board)

        self._board_msg.message = cast(list[discord.Message], self._board_msg)
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
    ) -> tuple[int, int] | tuple[str, None]:
        def chk(reaction: discord.Reaction, user: discord.User) -> bool:
            self._board_msg.message = cast(
                list[discord.Message], self._board_msg.message
            )
            return (
                user.id == this_turn.member.id
                and reaction.message == self._board_msg.message[1]
                and str(reaction.emoji) in NUM_EMOTES[:7]
            )

        timeout = False
        while True:
            try:
                reaction, user = await self._bot.wait_for(
                    'reaction_add', check=chk, timeout=self._wait_time
                )
                await reaction.remove(user)

                for k, num in enumerate(NUM_EMOTES):
                    if num == str(reaction.emoji):
                        if not await self._board.is_valid_square(k + 1, 0, '1'):
                            await self._prompt_msg.occupied(this_turn)
                            continue
                        return k + 1, 0
            except asyncio.TimeoutError:
                if timeout:
                    await self._prompt_msg.timeout(this_turn, next_turn)
                    return 'timeout', None
                timeout = True
                await self._prompt_msg.hurry(this_turn)
                continue


class ReversiBoard(BaseBoard):
    def __init__(self) -> None:
        super().__init__('🌑', '⚪', '🟩', 8, BaseSquare)
        self.rows = [
            [self._all_squares[self.length * y + x] for x in range(8)] for y in range(8)
        ]  # columns work with [x][y] access here too, instead of rows
        self.columns = [[r[n] for r in self.rows] for n in range(8)]
        self.columns[3][4].occupier = '2'
        self.columns[4][3].occupier = '2'
        self.columns[3][3].occupier = '1'
        self.columns[4][4].occupier = '1'
        r_diag_starts = (
            (0, 5),
            (0, 4),
            (0, 3),
            (0, 2),
            (0, 1),
            (0, 0),
            (1, 0),
            (2, 0),
            (3, 0),
            (4, 0),
            (5, 0),
        )
        l_diag_starts = (
            (0, 2),
            (0, 3),
            (0, 4),
            (0, 5),
            (0, 6),
            (0, 7),
            (1, 7),
            (2, 7),
            (3, 7),
            (4, 7),
            (5, 7),
        )
        self.right_diagonals: list[list[BaseSquare]] = [[] for _ in range(11)]
        self.left_diagonals: list[list[BaseSquare]] = [[] for _ in range(11)]
        for n in range(8):
            for k, right_list in enumerate(self.right_diagonals):
                try:
                    right_list.append(
                        self.columns[r_diag_starts[k][0] + n][r_diag_starts[k][1] + n]
                    )
                except IndexError:
                    continue
            for k, left_list in enumerate(self.left_diagonals):
                try:
                    if l_diag_starts[0][1] - n < 0:
                        continue
                    left_list.append(
                        self.columns[l_diag_starts[k][0] + n][l_diag_starts[k][1] - n]
                    )
                except IndexError:
                    continue

    async def to_emojis(self) -> tuple[str, str, str]:
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

    async def is_valid_square(self, x: int, y: int, value: Literal['1', '2']) -> bool:
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

        has_square: list[list[BaseSquare]] = []
        spans: list[tuple[int, int]] = []
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
    async def _find_across(
        lst: list[BaseSquare], char: str
    ) -> tuple[int, int] | tuple[()]:
        string = ''.join([square.occupier for square in lst])
        try:
            if char == '1':
                return re.search(r'1[12]*2[12]*1', string).span()  # type: ignore
            else:
                return re.search(r'2[12]*1[12]*2', string).span()  # type: ignore
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
        ctx: commands.Context[Vesuvius] | InteractionContextAdapter,
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
        boart1, board2, board3 = cast(
            tuple[str, str, str], await self._board.to_emojis()
        )
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
        assert self._start_time is not None
        delta: datetime.timedelta = datetime.datetime.now() - self._start_time
        if delta.seconds / 60 > self._time:
            await self._check_board_win(
                this_turn, next_turn, force=True, time_is_out=True
            )
            return True

        await self._prompt_msg.update(this_turn)
        return False

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

        black, white = cast(tuple[int, int], await self._board.check_win())
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
        self.up: Optional[WeiqiSquare] = None
        self.down: Optional[WeiqiSquare] = None
        self.right: Optional[WeiqiSquare] = None
        self.left: Optional[WeiqiSquare] = None

    @property
    def neighbors(self) -> list[WeiqiSquare]:
        return [
            sq for sq in [self.up, self.down, self.right, self.left] if sq is not None
        ]

    async def liberty(self) -> tuple[bool, set[WeiqiSquare]]:
        """checks this square's liberty

        returns a list of [liberty: bool, group: set[Square]]. liberty is if
        the group has liberty. group is a set of all squares of the connected group.
        """
        group: set[WeiqiSquare] = {self}
        return await self._liberty2(group), group

    async def _liberty2(self, group: set[WeiqiSquare]) -> bool:
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
        emptygroup: set[WeiqiSquare] = {self}
        surrounded: set[WeiqiSquare] = set(self.neighbors)
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

    async def _group2(self, gp: set[WeiqiSquare], sr: set[WeiqiSquare]) -> None:
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

        self._unliberated: set[WeiqiSquare] = set()
        self._numof_unlib: int = 0
        self._b_prisoners: int = 0
        self._w_prisoners: int = 0

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
        checked: set[WeiqiSquare] = set()
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
        ctx: commands.Context[Vesuvius] | InteractionContextAdapter,
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
            await self._ctx.send(
                embeds=cast(list[discord.Embed], await self._board.to_emojis())
            ),
            self._board,
        )
        self._prompt_msg = PromptMessage(
            await self._ctx.send(
                f"{self._player1.mention} {self._player1.symbol}'s turn!"
            )
        )
        return False

    async def _iter_begin(self, this_turn: Player, next_turn: Player) -> bool:
        assert self._start_time is not None
        delta: datetime.timedelta = datetime.datetime.now() - self._start_time
        if delta.seconds / 60 > self._time:
            await self._check_board_win(
                this_turn, next_turn, force=True, time_is_out=True
            )
            return True

        await self._prompt_msg.update(this_turn)
        return False

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

        black, white = cast(tuple[int, int], await self._board.check_win())
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


class BattleshipBoard(BaseBoard):
    def __init__(self, player: Player) -> None:
        super().__init__('⬜', '\U0001f7e9', '🟦', 10)
        self.player = player
        self.hit_ship = False
        self.sank_ship = False

        self.rows = [
            [self._all_squares[self.length * y + x] for x in range(10)]
            for y in range(10)
        ]
        self.columns = [[r[n] for r in self.rows] for n in range(10)]

        self.old_ships: list[BaseSquare] = []
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

    async def get_square(self, x: int | float, y: int | float) -> BaseSquare:
        """getter only for use with old_squares"""
        return self._all_squares[self.length * int(y) - self.length + int(x) - 1]

    async def initial_set_square(
        self, x: int | float, y: int | float, value: Literal['0', '1', '2']
    ):
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
            set_square.occupier = '💥'
            self.hit_ship = True
        for k, ship in enumerate(self.ships):
            this_squares: list[BaseSquare] = [
                self._all_squares[self.length * y - self.length + x - 1]
                for x, y in [(int(point.x), int(point.y)) for point in ship.allpoints]
            ]
            if all([square.occupier == '💥' for square in this_squares]):
                self.ships.pop(k)
                self.sank_ship = True
                for sq in this_squares:
                    sq.occupier = '🔥'
                break

    async def check_win(self) -> tuple[int, int]:
        remaining = 0
        for ship in self.ships:
            remaining += len(ship.allpoints)
        print('bd return remaining', remaining)
        return remaining, 0

    async def reveal_ships(self) -> None:
        for square in self.old_ships:
            if square.occupier == '0':
                square.occupier = '1'


class Timeout1(asyncio.TimeoutError):
    pass


class Timeout2(asyncio.TimeoutError):
    pass


class DirectionsButtonView(ui.View):
    SHIP_NAMES = ('Carrier', 'Battleship', 'Cruiser', 'Submarine', 'Destroyer')

    def __init__(self, superview: EphemeralBattleshipStartView, board: BattleshipBoard):
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

    async def wait(self) -> bool | NoReturn:
        res = await super().wait()
        if res:
            print('waiting', self.board.player.member)
            if self.board.player.member.id == self.superview.player1.member.id:
                raise Timeout1
            raise Timeout2
        return res

    async def handle_button_interaction(
        self, interaction: discord.Interaction, button: DirectionButton
    ):
        print('handling', self.board, interaction, button, button.direction)
        move_point: Optional[Point | tuple[Point, float]] = None
        match button.direction:
            case 'up':
                print('up up up')
                move_point = Point(0, 1)
                print(move_point)
            case 'down':
                move_point = Point(0, -1)
            case 'left':
                move_point = Point(-1, 0)
            case 'right':
                move_point = Point(1, 0)
            case 'rotate':
                print('spin spin spin')
                ship = self.board.ships[self._current_ship].allpoints
                move_point = (ship[len(ship) // 2], radians(90))
                print(ship, move_point, move_point[0].x, move_point[0].y)
            case _:  # case 'ok'
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
                    print('after usa')
                    print(interaction)
                    await interaction.response.edit_message(
                        content=f'{C.B}{C.BOLD_GRAY_H_INDIGO}{self.__class__.SHIP_NAMES[self._current_ship]}{C.E}',
                        embed=discord.Embed(description=await self.board.to_emojis()),
                        view=self,
                    )
                return

        print('fig mv o rt', move_point)

        await self.board_remove()
        for square in self.board.old_ships:
            square.occupier = '1'
        if not isinstance(move_point, tuple):
            print('mv pt mving')
            self.board.ships[self._current_ship].translate_all(move_point)
        else:
            print('rt pt rting')
            self.board.ships[self._current_ship].rotate_all(move_point)
        await self.board_add()
        await self.check_button_usable()
        print('\n', self.board, '\n')
        await interaction.response.edit_message(
            embed=discord.Embed(description=await self.board.to_emojis()), view=self
        )

    async def board_add(self):
        print('bd add')
        for x, y in [
            (point.x, point.y)
            for point in self.board.ships[self._current_ship].allpoints
        ]:
            await self.board.initial_set_square(x, y, '2')

    async def board_remove(self):
        print('bd rm')
        for x, y in [
            (point.x, point.y)
            for point in self.board.ships[self._current_ship].allpoints
        ]:
            await self.board.initial_set_square(x, y, '0')

    async def check_button_usable(self) -> None:
        print('chk btn usa')
        this_ship = [
            await self.board.get_square(point.x, point.y)
            for point in self.board.ships[self._current_ship].allpoints
        ]
        print('this ship', this_ship)
        for square in self.board.old_ships:
            if square in this_ship:
                self.children[2].disabled = True  # type: ignore
                break
        else:
            self.children[2].disabled = False  # type: ignore

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
                self.children[0].disabled = True  # type: ignore
                break
        else:
            self.children[0].disabled = False  # type: ignore

        print('bziter')
        for k, edge in zip(
            (1, 3, 4, 5),
            (
                self.board.rows[-1],
                self.board.columns[0],
                self.board.rows[0],
                self.board.columns[-1],
            ),
        ):
            print('ziter', k, edge)
            if any([point in edge for point in this_ship]):
                self.children[k].disabled = True  # type: ignore
            else:
                self.children[k].disabled = False  # type: ignore


class DirectionButton(ui.Button[DirectionsButtonView]):
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

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        print('pressed')
        await self.view.handle_button_interaction(interaction, self)


class EphemeralBattleshipStartView(ui.View):
    def __init__(self, bot: commands.Bot, p1: Player, p2: Player):
        super().__init__(timeout=20)
        self.bot = bot
        self.player1 = p1
        self.player2 = p2
        self.message: Optional[discord.Message] = None

        self.subview1: Optional[DirectionsButtonView] = None
        self.subview2: Optional[DirectionsButtonView] = None
        self.interaction1: Optional[discord.Interaction] = None
        self.interaction2: Optional[discord.Interaction] = None

        self.children: list[discord.Button]  # type: ignore

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
    async def press(
        self,
        interaction: discord.Interaction,
        button: ui.Button[EphemeralBattleshipStartView],
    ):
        this_board = BattleshipBoard(Player(cast(discord.Member, interaction.user)))
        for x, y in [(point.x, point.y) for point in this_board.ships[0].allpoints]:
            await this_board.initial_set_square(x, y, '2')
        buttons_view = DirectionsButtonView(self, this_board)
        assert self.message is not None
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

        self.red_hex = discord.Colour.from_rgb(255, 0, 0)
        self.blue_hex = discord.Colour.from_rgb(51, 153, 255)

    async def set_square(self, x: int, y: int, value: Literal['1', '2']) -> None:
        if value == '1':
            await self._board2.set_square(x, y, value)
            self.hit, self.sank = self._board2.hit_ship, self._board2.sank_ship
        else:
            await self._board1.set_square(x, y, value)
            self.hit, self.sank = self._board1.hit_ship, self._board1.sank_ship

    async def is_valid_square(self, x: int, y: int, value: Literal['1', '2']) -> bool:
        if value == '1':
            return await self._board2.is_valid_square(x, y, value)
        return await self._board1.is_valid_square(x, y, value)

    async def to_emojis(self) -> list[discord.Embed]:
        if self.this_turn == '1':
            title = "Blue's Ocean"
            desc = await self._board2.to_emojis()
            color = self.blue_hex
        else:
            title = "Red's Ocean"
            desc = await self._board1.to_emojis()
            color = self.red_hex
        return [discord.Embed(title=title, description=desc, colour=color)]

    async def check_win(self) -> tuple[int, int]:
        num1, num2 = await self._board1.check_win(), await self._board2.check_win()
        return num1[0], num2[0]

    async def reveal_ships(self) -> list[discord.Embed]:
        await self._board1.reveal_ships()
        await self._board2.reveal_ships()
        return [
            discord.Embed(
                title="Red's Ocean",
                description=await self._board1.to_emojis(),
                colour=self.red_hex,
            ),
            discord.Embed(
                title="Blue's Ocean",
                description=await self._board2.to_emojis(),
                colour=self.blue_hex,
            ),
        ]


class BattleshipGame(BaseGame):
    def __init__(
        self,
        ctx: commands.Context[Vesuvius] | InteractionContextAdapter,
        bot: commands.Bot,
        opponent: discord.Member,
    ) -> None:
        super().__init__(
            ctx,
            bot,
            opponent,
            object,  # type: ignore
            'Red',
            'Blue',
            C.RED,
            C.BLUE,
            200,
            r'(?P<x>[1-9]0??)[, ]*(?P<y>[1-9]0??)',
            45,
        )

    async def _loop_begin(self) -> bool:
        start_view = EphemeralBattleshipStartView(
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

        assert view1 and view2
        board1, board2 = view1.board, view2.board
        task = asyncio.gather(view1.wait(), view2.wait())
        try:
            await task
        except Timeout1:
            cancel_info = (
                cast(discord.Interaction, start_view.interaction2),
                view2,
                cast(discord.Interaction, start_view.interaction1),
                view1,
                self._player1,
            )
        except Timeout2:
            cancel_info = (
                cast(discord.Interaction, start_view.interaction1),
                view1,
                cast(discord.Interaction, start_view.interaction2),
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
        await self.cancel_buttons_view(view1)
        await self.cancel_buttons_view(view2)
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
        return False

    async def _iter_end(self, this_turn: Player, next_turn: Player) -> bool:
        if self._flush:
            self._flush = False
            await self._flush_channel()
        await self._board_msg.update()
        self._board: SingleBattleshipBoardAdapter
        if self._board.sank:
            await self._ctx.send(
                f'{C.B}{C.GREEN}Hit! and a ship has sunken!{C.E}', delete_after=3
            )
            await asyncio.sleep(3)
        elif self._board.hit:
            await self._ctx.send(f'{C.B}{C.GREEN}Hit!{C.E}', delete_after=2)
            await asyncio.sleep(2)
        else:
            await self._ctx.send(f'{C.B}{C.RED}Miss!{C.E}', delete_after=2)
            await asyncio.sleep(2)

        if await self._check_board_win(this_turn, next_turn):
            await self._board_msg.update_message(await self._board.reveal_ships())
            return True
        return False

    async def _timeout(self, this_turn: Player, next_turn: Player) -> None:
        await self._board_msg.update_message(await self._board.reveal_ships())
        await super()._timeout(this_turn, next_turn)

    async def _end(self, this_turn: Player, next_turn: Player) -> None:
        print('end call')
        await self._board_msg.update_message(await self._board.reveal_ships())
        await super()._end(this_turn, next_turn)

    async def _check_board_win(
        self, this_turn: Player, next_turn: Player, *, force: bool = False
    ) -> bool:
        red, blue = await self._board.check_win()
        print('checking', red, blue, force)
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
    async def cancel_buttons_view(view: ui.View):
        for child in view.children:
            print('cancel btn view disable', child)
            child.disabled = True  # type: ignore
        view.stop()

    async def cancel_messages(
        self,
        start_view: EphemeralBattleshipStartView,
        view1: DirectionsButtonView | None,
        view2: DirectionsButtonView | None,
    ) -> str:
        if not view1 and not view2:
            return f'{C.B}{C.RED}Timed out.{C.E}'
        if not view1:
            assert view2 and start_view.interaction2
            await self.cancel_buttons_view(view2)
            start_view.interaction2.message = (
                await start_view.interaction2.edit_original_message(
                    content=f'{C.B}{C.RED}Your opponent timed out.{C.E}', view=view2
                )
            )
            return f'{C.B}{C.RED}{self._player1} timed out.{C.E}'
        else:
            assert view1 and start_view.interaction1
            await self.cancel_buttons_view(view1)
            start_view.interaction1.message = (
                await start_view.interaction1.edit_original_message(
                    content=f'{C.B}{C.RED}Your opponent timed out.{C.E}', view=view1
                )
            )
            return f'{C.B}{C.RED}{self._player2} timed out.{C.E}'


class InteractionContextAdapter:
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.author = interaction.user
        self.channel = cast(discord.TextChannel, interaction.channel)
        self.send = self.channel.send

    async def reply(self, content: str, **kwargs: Any) -> discord.InteractionMessage:
        await self.interaction.response.send_message(content, **kwargs)
        self.interaction.message
        return await self.interaction.original_message()


class GameFeatures(commands.GroupCog, name='play'):
    def __init__(self, bot: Vesuvius) -> None:
        self.bot = bot
        self.ingame: list[int] = []
        super().__init__()

    @commands.command(name='ingames')
    @commands.dynamic_cooldown(owner_bypass(180), commands.BucketType.user)
    @commands.guild_only()
    async def ingames(self, ctx: commands.Context[Vesuvius], clear: str = ''):
        await ctx.send(f'```py\n{self.ingame}```')
        if clear == 'clear':
            self.ingame.clear()
            await ctx.send(f'{C.B}{C.GREEN}cleared!{C.E}')

    @commands.hybrid_command(name='tic-tac-toe')
    async def tictactoe(
        self,
        ctx_or_inter: commands.Context[Vesuvius] | discord.Interaction,
        opponent: discord.Member,
    ):
        if isinstance(ctx_or_inter, discord.Interaction):
            ctx = InteractionContextAdapter(ctx_or_inter)
        else:
            ctx = ctx_or_inter

        if await self.wait_confirm(ctx, opponent, 'Tic-Tac-Toe'):
            return

        game = TicTacToeGame(ctx, self.bot, opponent)
        await game.start()

        assert game.winner and game.loser
        await self.done_playing('tictactoe', game.winner, game.loser, game.tie)

    @commands.hybrid_command(name='connect-four')
    async def connectfour(
        self,
        ctx_or_inter: commands.Context[Vesuvius] | discord.Interaction,
        opponent: discord.Member,
    ):
        if isinstance(ctx_or_inter, discord.Interaction):
            ctx = InteractionContextAdapter(ctx_or_inter)
        else:
            ctx = ctx_or_inter

        if await self.wait_confirm(ctx, opponent, 'Connect-Four'):
            return

        game = ConnectFourGame(ctx, self.bot, opponent)
        await game.start()

        assert game.winner and game.loser
        await self.done_playing('connectfour', game.winner, game.loser, game.tie)

    @commands.hybrid_command(name='reversi')
    async def reversi(
        self,
        ctx_or_inter: commands.Context[Vesuvius] | discord.Interaction,
        opponent: discord.Member,
    ):
        if isinstance(ctx_or_inter, discord.Interaction):
            ctx = InteractionContextAdapter(ctx_or_inter)
        else:
            ctx = ctx_or_inter

        if await self.wait_confirm(ctx, opponent, 'Reversi'):
            return

        game = ReversiGame(ctx, self.bot, opponent)
        await game.start()

        assert game.winner and game.loser
        await self.done_playing('reversi', game.winner, game.loser, game.tie)

    @commands.hybrid_command(name='weiqi')
    async def weiqi(
        self,
        ctx_or_inter: commands.Context[Vesuvius] | discord.Interaction,
        opponent: discord.Member,
    ):
        if isinstance(ctx_or_inter, discord.Interaction):
            ctx = InteractionContextAdapter(ctx_or_inter)
        else:
            ctx = ctx_or_inter

        if await self.wait_confirm(ctx, opponent, 'Weiqi'):
            return

        game = WeiqiGame(ctx, self.bot, opponent)
        await game.start()

        assert game.winner and game.loser
        await self.done_playing('weiqi', game.winner, game.loser, game.tie)

    @commands.hybrid_command(name='battleship')
    async def battleship(
        self,
        ctx_or_inter: commands.Context[Vesuvius] | discord.Interaction,
        opponent: discord.Member,
    ):
        if isinstance(ctx_or_inter, discord.Interaction):
            ctx = InteractionContextAdapter(ctx_or_inter)
        else:
            ctx = ctx_or_inter

        if await self.wait_confirm(ctx, opponent, 'Battleship'):
            return

        game = BattleshipGame(ctx, self.bot, opponent)
        await game.start()

        assert game.winner and game.loser
        await self.done_playing('battleship', game.winner, game.loser, game.tie)

    async def wait_confirm(
        self,
        ctx: commands.Context[Vesuvius] | InteractionContextAdapter,
        opp: discord.Member,
        game: str,
    ) -> int:
        """wait for confirmation that the opp wants to play game"""
        if ctx.author.id in self.ingame:
            await ctx.send(f'{C.B}{C.RED}you are already in another game.{C.E}')
            return 1

        if opp.id in self.ingame:
            await ctx.send(
                f'{C.B}{C.RED}{opp.display_name} is already in another game. '
                f'wait for it to finish or try another person!{C.E}'
            )
            return 1

        if opp.id == ctx.author.id:
            await ctx.send(f'{C.B}{C.RED}you cannot challenge yourself.{C.E}')
            return 1

        if opp.id == cast(discord.User, self.bot.user).id:
            await ctx.send(f'{C.B}{C.RED}no.{C.E}')
            return 1

        self.ingame.append(ctx.author.id)
        invitation = await ctx.reply(
            f'{ctx.author.display_name} has challenged {opp.display_name} '
            f'to a match of {game}! {opp.mention}, do you accept? '
            '(react with :white_check_mark: or :negative_squared_cross_mark:)'
        )
        await invitation.add_reaction('✅')
        await invitation.add_reaction('❎')

        def chk(r: discord.Reaction, u: discord.User):
            return (
                u.id == opp.id
                and str(r.emoji) in '✅❎'
                and r.message.id == invitation.id
            )

        reaction = ''
        status = ''
        try:
            reaction, _ = await self.bot.wait_for('reaction_add', check=chk, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(
                f'{C.B}{C.RED}command timed out. it seems that {opp.display_name} '
                f'does not want to play rn. try someone else!{C.E}'
            )
            self.ingame.remove(ctx.author.id)
            status = 'ignored'
        if reaction:
            if str(reaction.emoji) == '❎':
                await invitation.reply(
                    f'{opp.display_name} did not accept the challenge.'
                )
                self.ingame.remove(ctx.author.id)
                status = 'rejected'
            elif str(reaction.emoji) == '✅':
                await invitation.reply(
                    f'{opp.display_name} has accepted the challenge!'
                )
                self.ingame.append(opp.id)
                status = 'accepted'
        now = datetime.datetime.now().strftime("%m/%d, %H:%M:%S")

        if game == 'go':
            game = 'weiqi'
        elif game == 'othello':
            game = 'reversi'

        async with aopen(self.bot.files['game_log'], 'a') as gl:
            await gl.write(
                f'{now} | {ctx.author.display_name}{game:>16} {opp.display_name:>17},{status:>18}\n'
            )
        if status in {'ignored', 'rejected'}:
            return 1
        return 0

    async def done_playing(
        self,
        game: str,
        p1: discord.Member | discord.User,
        p2: discord.Member | discord.User,
        tie: bool = False,
    ):
        print('done', p1, p2)
        self.ingame.remove(p1.id)
        self.ingame.remove(p2.id)
        await self.bot.database.set_games_winloss(p1.id, p2.id, game, tie)


async def setup(bot: Vesuvius):
    await bot.add_cog(GameFeatures(bot))
    print('LOADED games')
